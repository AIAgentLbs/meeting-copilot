"""One explicit retry at a time; durable request IDs survive browser retries."""
import re
import threading
from datetime import datetime, timezone
from delivery_settings import read_json, write_json, enabled


class DeliveryRetry:
    def __init__(self, archive):
        self.archive = archive
        self.lock = threading.Lock()
        self.job = {"state": "idle"}

    def snapshot(self):
        with self.lock:
            return dict(self.job)

    def submit(self, payload):
        identity = str(payload.get("meeting_id", ""))
        request = str(payload.get("request_id", ""))
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,120}", identity) or not re.fullmatch(r"[A-Za-z0-9_-]{16,80}", request):
            raise ValueError("invalid_retry_request")
        channels = payload.get("channels")
        if not isinstance(channels, list) or not channels or any(c not in {"email", "drive", "telegram"} for c in channels):
            raise ValueError("invalid_retry_channels")
        with self.lock:
            if self.job.get("state") == "sending":
                if self.job.get("request_id") == request:
                    return dict(self.job)
                raise ValueError("delivery_busy")
            self.job = {"state": "sending", "request_id": request, "meeting_id": identity}
            thread = threading.Thread(target=self._run, args=(identity, request, set(channels), payload.get("confirm") is True), daemon=True)
            thread.start()
            return dict(self.job)

    def _run(self, identity, request, channels, confirm):
        result = {"state": "failed", "request_id": request, "meeting_id": identity}
        try:
            with self.archive.lock:
                path = self.archive.reports_root / identity / "report.json"
                report = read_json(path)
                if not report:
                    raise ValueError("report_not_ready")
                if report.get("last_delivery_request") == request:
                    result.update(state="complete", report=report.get("last_delivery_result", {}))
                else:
                    detail = self.archive.report_detail(identity)
                    if not detail or not self.archive._ready_for_delivery(detail):
                        raise ValueError("meeting_not_finished")
                    pdf = self.archive.report_path(identity, "meeting-report.pdf")
                    if not pdf or not pdf.is_file():
                        raise ValueError("report_not_ready")
                    settings = self.archive.delivery_settings.read()
                    if any(not enabled(settings, c) for c in channels):
                        raise ValueError("channel_disabled")
                    fields = {"email": "mail_status", "drive": "drive_status", "telegram": "telegram_status"}
                    acknowledged = {**report, **read_json(path.parent / "delivery-receipts.json")}
                    if not confirm and any(acknowledged.get(fields[c]) in {"sent", "uploaded", "unknown"} for c in channels):
                        raise ValueError("resend_confirmation_required")
                    previous = dict(report)
                    for channel in channels:
                        previous[fields[channel]] = "pending"
                    previous.pop("mail_error", None)
                    # Persist uncertainty BEFORE the send; a crash must never
                    # trigger an unconfirmed automatic duplicate on restart.
                    report["last_delivery_request"] = request
                    report["last_delivery_result"] = {"state": "outcome_unknown"}
                    if "email" in channels:
                        report["mail_status"] = "unknown"
                    write_json(path, report)
                    delivery = self.archive.deliver(detail, {**report, "pdf_path": str(pdf)},
                                                    previous=previous, channels=channels, manual=True)
                    report.update(delivery)
                    report["delivery_checked_at"] = datetime.now(timezone.utc).isoformat()
                    report["last_delivery_result"] = delivery
                    write_json(path, report)
                    result.update(state="complete", report=delivery)
        except ValueError as error:
            result["error"] = str(error)
        except Exception:
            result["error"] = "delivery_failed"
        finally:
            with self.lock:
                self.job = result
            self.archive.check_delivery_health()

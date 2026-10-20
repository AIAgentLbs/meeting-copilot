import Foundation

/// Turns a finished transcript into `summary.md`.
///
/// It runs on the AI chosen for `ai.purposes.summary` (see `LLMBackend`) and
/// on nothing else; with no choice made it waits for one.
///
/// Nothing here is allowed to fail loudly. A missing summary is an
/// inconvenience; a transcript lost because summarizing threw is a lost
/// meeting. Every path logs and returns.
enum Summarizer {
    /// Above this, the transcript is summarized in pieces and the pieces are
    /// summarized together. Comfortably inside every backend's context window,
    /// including a small local model's.
    private static let maxCharsPerCall = 60_000

    /// Write summary.md for a finished session. Returns the backend that
    /// produced it, or nil if summarization is off or every backend failed.
    @discardableResult
    static func summarize(
        transcript: Transcript,
        context: [String],
        into dir: URL
    ) async -> String? {
        func log(_ message: String) { appendSessionLog(message, to: dir) }

        let settings = Config.summary()
        guard settings.writesSummaries else { return nil }

        let body = plainText(transcript)
        guard !body.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            log("summary skipped — the transcript is empty")
            return nil
        }

        let backend: LLMBackend
        switch LLMBackend.resolve(.summary) {
        case .ready(let chosen): backend = chosen
        case let other:
            // Not a failure of this meeting: once an AI is chosen, the next
            // pass writes the summary.
            log("summary not written — \(other.problem ?? AIChoice.needsChoiceMessage)")
            SessionState.update(dir, with: [SessionState.Key.summaryStatus: SessionState.needsChoice])
            return nil
        }

        // Whatever we know about the meeting, above the transcript. Names in
        // particular: given a participant list, the summarizer writes "Anna
        // will send the contract" instead of "them will send the contract".
        let header = context.isEmpty ? "" : context.joined(separator: "\n") + "\n"
        do {
            log("summarizing with \(backend.name) (\(backend.model))")
            let reply = try await produce(
                body: body, header: header, settings: settings, backend: backend
            )
            let text = reply.text.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !text.isEmpty else { throw LLMError.emptyResponse(backend.name) }
            try Data((text + "\n").utf8).write(
                to: dir.appendingPathComponent("summary.md"), options: .atomic
            )
            log("summary written by \(backend.name) (model \(reply.model))")
            SessionState.update(dir, with: [SessionState.Key.summaryStatus: nil])
            return backend.name
        } catch {
            // Record which kind of failure, so a later pass can tell "come
            // back to this" from "this will never work". A summary missed on
            // a plane should still get written that evening.
            let transient = LLMError.isTransient(error)
            SessionState.update(dir, with: [
                SessionState.Key.summaryStatus: transient ? SessionState.deferred : "failed",
            ])
            log(LLMError.isUsageLimit(error)
                ? "\(backend.name) is out of allowance — summary deferred, will be retried later"
                : transient
                    ? "summary via \(backend.name) deferred: \(error)"
                    : "summary via \(backend.name) failed for good: \(error)")
            return nil
        }
    }

    // MARK: - prompting

    private static func systemPrompt(language: String?) -> String {
        let target = language.map { "Write the note in \($0)." }
            ?? "Write the note in the same language the meeting was held in."
        return """
        You are taking notes on a meeting from its transcript.
        \(target) Translate the section headings into that language too.
        Invent nothing that isn't in the transcript. If something never came up, say so.
        The transcript is machine-made and contains recognition errors — read past odd \
        words rather than treating them as meaningful.
        Speakers are labelled "me" (the person recording) and "them" (everyone else).
        """
    }

    private static let summaryInstructions = """
    Below is a meeting transcript with speaker labels.

    Write a Markdown note with exactly this structure:

    ## What this was about
    Two or three sentences: the topic and why they met.

    ## Key points
    5–10 substantive bullets. Each one a complete thought, not a fragment.

    ## Decisions
    What was decided. If nothing was, say that plainly.

    ## Action items
    Lines of "— who: what to do (deadline, if one was named)". If there are none, say so.

    ## Open questions
    What was left unresolved. Skip the section entirely if there's nothing.

    No preamble, no "here's your note" — start with the Markdown.
    """

    private static let chunkInstructions = """
    Below is one part of a long meeting transcript. Write a compact set of notes on it:
    what was discussed, what was decided, which tasks and questions came up.
    Facts from this part only, no preamble.
    """

    private static let mergeInstructions = """
    Below are consecutive notes on parts of a single meeting. Combine them into one note.
    """

    private static func produce(
        body: String,
        header: String,
        settings: Config.SummarySettings,
        backend: LLMBackend
    ) async throws -> LLMReply {
        let system = systemPrompt(language: settings.language)
        let limit = chunkLimit(
            backendLimit: try await backend.inputLimit(),
            overhead: system.count + header.count + chunkInstructions.count + summaryInstructions.count + 64)
        if body.count <= limit {
            return try await backend.call(
                system, "\(header)\n\(summaryInstructions)\n\n---\n\(body)"
            )
        }

        let chunks = split(body, limit: limit)
        var notes: [String] = []
        for (index, chunk) in chunks.enumerated() {
            notes.append(try await backend.call(
                system,
                "\(header)Part \(index + 1) of \(chunks.count).\n\(chunkInstructions)\n\n---\n\(chunk)"
            ).text)
        }
        return try await backend.call(
            system,
            "\(header)\n\(mergeInstructions)\n\(summaryInstructions)\n\n---\n"
                + notes.joined(separator: "\n\n---\n\n")
        )
    }

    /// The transcript as the summarizer sees it: one speaker-tagged line per
    /// segment, timestamps dropped — they cost tokens and add nothing to a
    /// summary.
    private static func plainText(_ transcript: Transcript) -> String {
        transcript.segments
            .map { "\($0.speaker): \($0.text)" }
            .joined(separator: "\n")
    }

    /// Transcript characters per call: the usual size, or less when the
    /// backend's own limit (minus the prompt around the transcript) is smaller.
    static func chunkLimit(backendLimit: Int?, overhead: Int) -> Int {
        // Nothing fits: keep the usual size so the call fails with the
        // backend's own "too long" error instead of a flood of tiny calls.
        guard let backendLimit, backendLimit - overhead > 0 else { return maxCharsPerCall }
        return min(maxCharsPerCall, backendLimit - overhead)
    }

    /// Split on line boundaries so a chunk never ends mid-sentence.
    private static func split(_ text: String, limit: Int) -> [String] {
        var chunks: [String] = []
        var current: [String] = []
        var size = 0
        for line in text.split(separator: "\n", omittingEmptySubsequences: false) {
            if size + line.count > limit && !current.isEmpty {
                chunks.append(current.joined(separator: "\n"))
                current = []
                size = 0
            }
            current.append(String(line))
            size += line.count + 1
        }
        if !current.isEmpty { chunks.append(current.joined(separator: "\n")) }
        return chunks
    }

}

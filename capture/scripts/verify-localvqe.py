#!/usr/bin/env python3

import ctypes
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / ".build" / "localvqe"
LIBRARY = ASSETS / "lib" / "liblocalvqe.dylib"
MODEL = ASSETS / "model" / "localvqe-v1.4-aec-200K-f32.gguf"
EXPECTED_MODEL_SHA = "b6e43138588a83bfe903ab5e143b4020b91c1e1629f5a575ac5855ff0003c731"


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> None:
    if not LIBRARY.is_file() or not MODEL.is_file():
        fail("LocalVQE assets are missing; run scripts/build-localvqe.sh")
    if hashlib.sha256(MODEL.read_bytes()).hexdigest() != EXPECTED_MODEL_SHA:
        fail("LocalVQE model SHA-256 mismatch")
    arches = subprocess.check_output(["lipo", "-archs", LIBRARY], text=True).split()
    if set(arches) != {"arm64", "x86_64"}:
        fail(f"LocalVQE is not universal: {arches}")

    library = ctypes.CDLL(str(LIBRARY))
    library.localvqe_new.argtypes = [ctypes.c_char_p]
    library.localvqe_new.restype = ctypes.c_size_t
    library.localvqe_free.argtypes = [ctypes.c_size_t]
    library.localvqe_sample_rate.argtypes = [ctypes.c_size_t]
    library.localvqe_sample_rate.restype = ctypes.c_int
    library.localvqe_hop_length.argtypes = [ctypes.c_size_t]
    library.localvqe_hop_length.restype = ctypes.c_int
    library.localvqe_process_frame_f32.argtypes = [
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_float),
        ctypes.POINTER(ctypes.c_float),
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_float),
    ]
    library.localvqe_process_frame_f32.restype = ctypes.c_int

    context = library.localvqe_new(str(MODEL).encode())
    if not context:
        fail("LocalVQE could not load its model")
    try:
        if library.localvqe_sample_rate(context) != 16_000:
            fail("LocalVQE model is not 16 kHz")
        if library.localvqe_hop_length(context) != 256:
            fail("LocalVQE model does not use 256-sample hops")
        mic = (ctypes.c_float * 256)(*([0.1] * 256))
        far = (ctypes.c_float * 256)(*([0.0] * 256))
        output = (ctypes.c_float * 256)()
        result = library.localvqe_process_frame_f32(context, mic, far, 256, output)
        if result != 0 or not all(float("-inf") < value < float("inf") for value in output):
            fail(f"LocalVQE frame smoke test failed: {result}")
    finally:
        library.localvqe_free(context)

    verification = json.loads((ASSETS / "verification.json").read_text())
    if verification["model_sha256"] != EXPECTED_MODEL_SHA:
        fail("LocalVQE verification manifest disagrees with the model")
    print(f"LocalVQE verified: {' '.join(arches)}, 16 kHz, 256-sample hops")


if __name__ == "__main__":
    main()

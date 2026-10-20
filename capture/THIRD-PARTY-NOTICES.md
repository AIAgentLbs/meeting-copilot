# Third-party notices

Meeting Copilot includes the following open-source components. Exact copies of their
license texts are included in every application bundle under
`Contents/Resources/Licenses`.

| Component | Version | License |
|---|---:|---|
| [LocalVQE](https://github.com/localai-org/LocalVQE) (echo canceller) | f53063c | Apache License 2.0 |
| [ggml](https://github.com/ggml-org/ggml), distributed with LocalVQE | c044a8e | MIT |
| [FluidAudio](https://github.com/FluidInference/FluidAudio) | 0.15.5 | Apache License 2.0 |
| fastcluster, distributed with FluidAudio | bundled | BSD 2-Clause |
| vbx, distributed with FluidAudio | bundled | Apache License 2.0 |
| [swift-argument-parser](https://github.com/apple/swift-argument-parser) | 1.8.2 | Apache License 2.0 |
| [Sparkle](https://github.com/sparkle-project/Sparkle) | 2.9.6 | MIT and bundled external notices |
| Ed25519 verification code distributed with Sparkle | bundled | zlib-style license |

Meeting Copilot itself is available under the [MIT license](LICENSE).

The LocalVQE build uses a small macOS packaging patch to produce one
self-contained Intel dylib instead of runtime-loaded CPU-variant libraries.
The inference implementation and model are otherwise the pinned upstream work.

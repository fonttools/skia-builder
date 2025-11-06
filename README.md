# skia-builder

[![Build + Deploy](https://github.com/fonttools/skia-builder/actions/workflows/ci.yml/badge.svg)](https://github.com/fonttools/skia-builder/actions/workflows/ci.yml)

Builds Skia libraries for multiple platforms and architectures (static for macOS/Linux, shared for Windows).

Used by [skia-pathops](https://github.com/fonttools/skia-pathops) to provide precompiled Skia binaries for Python wheels.

## Releases

CI builds are triggered on tags. Release assets include:
- `libskia-mac-x64.zip`, `libskia-mac-arm64.zip`, `libskia-mac-universal2.zip`
- `libskia-linux-x64.zip`, `libskia-linux-arm64.zip`
- `libskia-win-x86.zip`, `libskia-win-x64.zip`

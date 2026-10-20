#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -lt 5 ] || [ "$#" -gt 6 ]; then
    echo "usage: $0 SOURCE SOURCE_REV GGML_REV PARENT_DIFF_SHA GGML_DIFF_SHA [--allow-unpatched-ggml]" >&2
    exit 2
fi

SOURCE=$1
SOURCE_REV=$2
GGML_REV=$3
PARENT_DIFF_SHA=$4
GGML_DIFF_SHA=$5
MODE=${6:-}
GGML="$SOURCE/ggml/vendor/ggml"
EMPTY_DIFF_SHA="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

if [ -n "$MODE" ] && [ "$MODE" != "--allow-unpatched-ggml" ]; then
    echo "unknown LocalVQE source verification mode: $MODE" >&2
    exit 2
fi

git -C "$SOURCE" rev-parse --git-dir >/dev/null 2>&1 \
    || { echo "LocalVQE source is not a git checkout" >&2; exit 1; }
git -C "$GGML" rev-parse --git-dir >/dev/null 2>&1 \
    || { echo "ggml source is not a git checkout" >&2; exit 1; }
test "$(git -C "$SOURCE" rev-parse HEAD)" = "$SOURCE_REV" \
    || { echo "LocalVQE source is not pinned at $SOURCE_REV" >&2; exit 1; }
test "$(git -C "$GGML" rev-parse HEAD)" = "$GGML_REV" \
    || { echo "ggml source is not pinned at $GGML_REV" >&2; exit 1; }

# Compare every tracked parent file to HEAD, including staged changes. The
# nested repository is checked independently so its dirty gitlink marker does
# not alter the approved parent patch digest.
# Full object IDs keep the digest independent of clone size and core.abbrev.
ACTUAL_PARENT_DIFF_SHA=$(
    git -C "$SOURCE" diff --binary --full-index HEAD -- . ':(exclude)ggml/vendor/ggml' \
        | shasum -a 256 | awk '{print $1}'
)
if [ "$ACTUAL_PARENT_DIFF_SHA" != "$PARENT_DIFF_SHA" ]; then
    echo "LocalVQE source contains unexpected tracked changes" >&2
    exit 1
fi

ACTUAL_GGML_DIFF_SHA=$(
    git -C "$GGML" diff --binary --full-index HEAD -- . \
        | shasum -a 256 | awk '{print $1}'
)
if [ "$ACTUAL_GGML_DIFF_SHA" != "$GGML_DIFF_SHA" ]; then
    if [ "$MODE" != "--allow-unpatched-ggml" ] \
        || [ "$ACTUAL_GGML_DIFF_SHA" != "$EMPTY_DIFF_SHA" ]; then
        echo "ggml source contains unexpected tracked changes" >&2
        exit 1
    fi
fi

test -z "$(git -C "$SOURCE" ls-files --others --exclude-standard)" \
    || { echo "LocalVQE source contains unexpected untracked files" >&2; exit 1; }
test -z "$(git -C "$GGML" ls-files --others --exclude-standard)" \
    || { echo "ggml source contains unexpected untracked files" >&2; exit 1; }

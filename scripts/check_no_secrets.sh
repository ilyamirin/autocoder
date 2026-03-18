#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

patterns=(
  'sk-[A-Za-z0-9]{20,}'
  'BEGIN (RSA|DSA|EC|OPENSSH|PRIVATE) KEY'
)

for pattern in "${patterns[@]}"; do
  if rg -n --hidden --glob '!data/**' --glob '!.git/**' --glob '!.env.example' "$pattern" .; then
    echo "Potential secret match found for pattern: $pattern" >&2
    exit 1
  fi
done

if rg -n -P --hidden --glob '!data/**' --glob '!.git/**' --glob '!.env.example' \
  '(OPENAI_API_KEY|KANBOARD_.*PASSWORD|GITEA_.*PASSWORD|WOODPECKER_.*SECRET)=(?!replace-me|replace-me@example.com)[^[:space:]]+' .; then
  echo "Potential concrete credential value found in tracked files." >&2
  exit 1
fi

echo "Secret scan passed."

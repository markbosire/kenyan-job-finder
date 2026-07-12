#!/bin/sh
# Combine all project Python files into combined.txt with path headers.
DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="$DIR/combined.txt"
> "$OUT"

find "$DIR" -name '*.py' \
  -not -path "$DIR/.venv/*" \
  -not -path "$DIR/__pycache__/*" \
  -not -path "$DIR/data/*" \
  -not -path "$DIR/output/*" \
  | sort \
  | while IFS= read -r f; do
      rel="$(echo "$f" | sed "s|$DIR/||")"
      printf '========================================================================\n' >> "$OUT"
      printf "FILE: %s\n" "$rel" >> "$OUT"
      printf '========================================================================\n\n' >> "$OUT"
      cat "$f" >> "$OUT"
      printf '\n\n' >> "$OUT"
    done

echo "Written $(find "$DIR" -name '*.py' -not -path "$DIR/.venv/*" -not -path "$DIR/__pycache__/*" -not -path "$DIR/data/*" -not -path "$DIR/output/*" | wc -l) files to $OUT"
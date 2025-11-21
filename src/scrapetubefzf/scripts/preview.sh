#!/usr/bin/env bash

VIDEO_ID="${1%%	*}"  # Keep up to the tab
THUMB_PATH="${CACHE_DIR}/$VIDEO_ID.jpg"

# Wait for thumbnail
for _ in {1..1000}; do
  [ -f "$THUMB_PATH" ] && break
  sleep 0.2
done

# Show thumbnail
if [ -f "$THUMB_PATH" ]; then
  if [ -n "$UEBERZUG_FIFO" ]; then
    echo '{"action": "add", "identifier": "fzf", "x": '$FZF_PREVIEW_LEFT', "y": '$FZF_PREVIEW_TOP', "max_width": '$FZF_PREVIEW_COLUMNS', "max_height": '$FZF_PREVIEW_LINES', "path": "'$THUMB_PATH'"}' >> "$UEBERZUG_FIFO"
  elif command -v chafa >/dev/null 2>&1; then
    chafa -s "$((FZF_PREVIEW_COLUMNS))x$((FZF_PREVIEW_LINES))" "$THUMB_PATH"
  elif command -v catimg >/dev/null 2>&1; then
    catimg -w "$((FZF_PREVIEW_COLUMNS))" "$THUMB_PATH"
  else
    echo "Thumbnail available at: $THUMB_PATH"
    echo "Install ueberzug, chafa, or catimg to view thumbnails in terminal"
  fi
fi

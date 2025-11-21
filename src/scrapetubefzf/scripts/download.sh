#!/usr/bin/env bash

IFS=$'\n'
SELECTED=($@)
i=0
for LINE in "${SELECTED[@]}"; do
   if (( i % 2 == 0 )); then
       VIDEO_ID="${LINE%%	*}"  # Keep up to the tab
       yt-dlp "https://www.youtube.com/watch?v=$VIDEO_ID"
   fi
   ((i++))
done

touch "$CACHE_DIR/alt-d.$MAIN_PID"
read -p "Press Enter to exit..."

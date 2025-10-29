#!/bin/bash

IFS=$'\n'
SELECTED=($@)
URLS=""
i=0
for LINE in "${SELECTED[@]}"; do
   if (( i % 2 == 0 )); then
       VIDEO_ID="${LINE%%	*}"  # Keep up to the tab
       yt-dlp "https://www.youtube.com/watch?v=$VIDEO_ID"
   fi
   ((i++))
done

read -p "Press Enter to exit..."

#!/usr/bin/env bash

IFS=$'\n'
TAB=$'\t'
SELECTED=($@)
N=$(( ${#SELECTED[@]} / 2 ))  # Number of selected videos

# Show selections
printf "Selected $N video$([ $N -ne 1 ] && echo "s"):\n"
if [ $N -eq 1 ]; then
    video_title="${SELECTED[0]#*$TAB}"  # Keep after the tab
    printf "    %s\n" "$video_title"
else
    i=0
    while [ $i -lt $N ]; do
        video_title="${SELECTED[$(( 2 * i ))]#*$TAB}"  # Keep after the tab
        printf "%4d. %s\n" "$(( i + 1 ))" "$video_title"
        ((i++))
    done
fi

# Download selections
printf "Downloading $N video$([ $N -ne 1 ] && echo "s") with yt-dlp...\n"
i=0
while [ $i -lt $N ]; do
    video_id="${SELECTED[$(( 2 * i ))]%%$TAB*}"  # Keep up to the tab
    yt-dlp "https://www.youtube.com/watch?v=$video_id"
    ((i++))
done

touch "$CACHE_DIR/alt-d.$MAIN_PID"

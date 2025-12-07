#!/usr/bin/env bash

IFS=$'\n'
TAB=$'\t'
SELECTED=($@)
N=$(( ${#SELECTED[@]} / 2 ))  # Number of selected results

# Show selections
printf "Selected $N result$([ $N -ne 1 ] && echo "s"):\n"
if [ $N -eq 1 ]; then
    result_title="${SELECTED[0]#*$TAB}"  # Keep after the tab
    printf "    %s\n" "$result_title"
else
    i=0
    while [ $i -lt $N ]; do
        result_title="${SELECTED[$(( 2 * i ))]#*$TAB}"  # Keep after the tab
        printf "%4d. %s\n" "$(( i + 1 ))" "$result_title"
        ((i++))
    done
fi

# Download selections
printf "Downloading $N selection$([ $N -ne 1 ] && echo "s") with yt-dlp...\n"
i=0
while [ $i -lt $N ]; do
    selection_id="${SELECTED[$(( 2 * i ))]%%$TAB*}"  # Keep up to the tab
    if [[ $selection_id =~ ^[a-zA-Z0-9_-]{11}$ ]]; then
        yt-dlp "https://www.youtube.com/watch?v=$selection_id"
    else
        yt-dlp "https://www.youtube.com/channel/$selection_id"
    fi
    ((i++))
done

touch "$CACHE_DIR/alt-d.$MAIN_PID"

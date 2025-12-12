#!/usr/bin/env bash

if [ -p "$UEBERZUG_FIFO" ]; then
    echo '{"action": "remove", "identifier": "fzf"}' >> "$UEBERZUG_FIFO"
fi

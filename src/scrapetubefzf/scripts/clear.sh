#!/usr/bin/env bash

if [ -f "$UEBERZUG_FIFO" ]; then
    echo '{"action": "remove", "identifier": "fzf"}' >> "$UEBERZUG_FIFO"
fi

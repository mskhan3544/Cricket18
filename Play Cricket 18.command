#!/bin/sh
# Starts the Cricket 18 browser server and opens the game. Close this window to stop it.
D="$HOME/Downloads/Cricket18"
URL="http://localhost:8007/"
if curl -s -o /dev/null "$URL"; then
    echo "Cricket 18 is already running."
    open "$URL"
    exit 0
fi
(sleep 2; open "$URL") &
echo "Cricket 18 is running at $URL"
echo "Keep this window open while you play. Close it (or press Ctrl+C) to stop."
exec "$D/toolchain/python/bin/python3" "$D/cricket18-browser/web/serve.py" --port 8007 --game "$D/Cricket18-Browser-Game"

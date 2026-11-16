#!/bin/zsh
cd "$(dirname "$0")"
if [ -d /Library/TeX/texbin ]; then
  export PATH="/Library/TeX/texbin:$PATH"
fi
echo "Starting Job Apply at http://127.0.0.1:8765"
echo "All CV and cover-letter files stay on this Mac unless you manually share them."
echo "Keep this Terminal window open while using Job Apply."
python3 app/server.py

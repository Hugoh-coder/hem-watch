#!/bin/zsh
# Daily refresh: scrape -> build -> push. Run by launchd (com.hugo.hem-watch)
# at 06:30; launchd fires missed runs after wake. Logs to refresh.log.
set -e
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

uv run watch.py
python3 build_site.py

git add docs matches.json seen_ids.json desc_cache.json
if git diff --cached --quiet; then
  echo "$(date '+%F %T') no changes"
else
  git commit -q -m "Refresh listings ($(date +%F))"
  git pull --rebase --autostash -q origin main
  git push -q origin main
  echo "$(date '+%F %T') pushed refresh"
fi

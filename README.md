# LinkedIn Game Dashboard

Standings for LinkedIn's daily puzzles (Queens, Tango, Zip, Mini Sudoku, Wend, Patches) among five players.

- `index.html`: standings, daily results grid, time trend, recent scores.
- `player.html?p=<name>`: one player's wins, average position, average time and more. Opened by clicking a name.
- `shared.js`, `style.css`: scoring, filters and styles used by both pages.
- `data.json`: the scores. `scrape.py` fills it in; `validate.py` checks it.

Scoring: the fastest time wins each puzzle each day, ties share the win, and a hint adds 60 seconds.
Position is the rank among the tracked players for that puzzle and day.

Run locally (the pages fetch `data.json`, so they need a web server):

    python3 -m http.server

Update scores: `.venv/bin/python scrape.py` (opens a browser; you log in to LinkedIn yourself), then `python3 validate.py`.

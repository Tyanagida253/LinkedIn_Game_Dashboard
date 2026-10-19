# Run before committing: python3 validate.py
import json,re,sys
GAMES={"Queens","Tango","Zip","Mini Sudoku","Wend","Patches"}
PLAYERS={"Tyler Yanagida","Oscar Gidley-Kitchin","Sophie Evans","Lucie Day"}
d=json.load(open("data.json")); seen=set(); errs=[]
for i,s in enumerate(d["scores"]):
    k=(s.get("date"),s.get("game"),s.get("player"))
    if not re.fullmatch(r"\d{4}-\d\d-\d\d",str(k[0])): errs.append(f"#{i} bad date {k[0]}")
    if k[1] not in GAMES: errs.append(f"#{i} unknown game {k[1]}")
    if k[2] not in PLAYERS: errs.append(f"#{i} unknown player {k[2]}")
    t=s.get("timeSeconds")
    if not isinstance(t,int) or not 1<=t<=3600: errs.append(f"#{i} implausible time {t}")
    if k in seen: errs.append(f"#{i} duplicate {k}")
    seen.add(k)
days = {}
for s in d["scores"]: days.setdefault(s["date"], []).append(bool(s.get("hints")))
for day, h in sorted(days.items()):  # warning only: this pattern is what a hint-detection bug looks like
    if len(h) >= 6 and sum(h) > len(h) / 2: print(f"WARNING: {day}: {sum(h)} of {len(h)} scores marked as hints. Check against the leaderboards.")
print("\n".join(errs) or f"OK: {len(seen)} scores"); sys.exit(bool(errs))

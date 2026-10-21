# Fetch today's LinkedIn Games leaderboards into data.json. Usage: .venv/bin/python scrape.py [--force]
# You log in yourself in the browser window (password never touches this script); only session
# cookies persist, in .browser-profile/ (delete it to log out). Read-only: loads pages, clicks only "See full leaderboard".
import json, random, re, shutil, subprocess, sys, time
from datetime import date, datetime
from pathlib import Path

GAMES = {"queens": "Queens", "tango": "Tango", "zip": "Zip", "mini-sudoku": "Mini Sudoku", "wend": "Wend", "patches": "Patches"}
PLAYERS = {"You": "Tyler Yanagida", "Oscar Gidley-Kitchin": "Oscar Gidley-Kitchin", "Sophie Evans": "Sophie Evans", "Lucie Day": "Lucie Day"}
LAST_RUN, MIN_GAP_H = Path(".last-run"), 20
TIME = re.compile(r"^(?:(\d+):(\d\d)|-:--)$")
KNOWN_BADGE = re.compile(r"no hints|no mistakes|no backtracks|no redraws|top \d+%|win by win", re.I)


def has_letter(l):
    return any(c.isalpha() for c in l)


def is_decor(l):
    """Lines that sit between a name and its time: rank digits, emoji-led lines (reactions, streak badges), and badges like 'No hints & no mistakes!'."""
    return not has_letter(l) or not l[0].isalnum() or l.endswith("!") or "no hints" in l.lower()


def parse(text):
    """Leaderboard text -> [(name, seconds, hints, badges)]; seconds is None for unplayed (-:--) rows.
    The name is the nearest non-decor line above the time. A row used hints unless a badge says 'No hints' (alone or as 'No hints & ...')."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    rows = []
    for i, l in enumerate(lines):
        m = TIME.match(l)
        if not m:
            continue
        j = i - 1
        while j >= 0 and not TIME.match(lines[j]) and is_decor(lines[j]):
            j -= 1
        if j < 0 or TIME.match(lines[j]):
            raise ValueError(f"no name found above time {l!r}")
        badges = [b for b in lines[j + 1:i] if has_letter(b)]
        rows.append((lines[j], int(m[1]) * 60 + int(m[2]) if m[1] else None, not any("no hints" in b.lower() for b in badges), badges))
    return rows


def check_complete(text, rows):
    """Every tracked player named on the page must have a parsed row, or a parser bug is silently dropping people."""
    on_page, got = {l.strip() for l in text.splitlines()}, {r[0] for r in rows}
    missing = [n for n in PLAYERS if n in on_page and n not in got]
    if missing:
        raise ValueError(f"{', '.join(missing)} appear on the page but were not parsed")


def scroll_rows(page):
    """Scroll until all tracked players are listed, 2 scrolls in a row add no names, or 10 scrolls are done.
    A name's first row wins: later blocks (such as your own summary card) repeat 'You' with different badges."""
    found, idle = {}, 0
    page.mouse.move(640, 450)
    for _ in range(11):
        text = "\n".join(f.inner_text("body") for f in page.frames)
        rows = parse(text)
        check_complete(text, rows)
        new = {r[0] for r in rows} - found.keys()
        for n, s, h, b in rows:
            found.setdefault(n, (s, h, b))
        idle = 0 if new else idle + 1
        if PLAYERS.keys() <= found.keys() or idle >= 2:
            break
        page.mouse.wheel(0, 800)
        page.wait_for_timeout(1500)
    for n, (_, _, badges) in found.items():
        for b in badges if n in PLAYERS else []:
            if not KNOWN_BADGE.search(b):
                print(f"  WARNING: unrecognised badge for {n}: {b!r}. Check the hints flag is right.")
    return [(PLAYERS[n], s, h) for n, (s, h, _) in found.items() if n in PLAYERS and s is not None]


def blocked(page):
    u = page.url
    return any(k in u for k in ("checkpoint", "challenge", "authwall", "login", "uas/")) or any(k in page.inner_text("body").lower() for k in ("captcha", "security verification", "quick security check"))


def load(page, url):
    resp = page.goto(url)
    if resp and resp.status == 429:
        sys.exit("LinkedIn returned 429 (rate limited). Stopping; try again tomorrow.")
    page.wait_for_timeout(4000)
    if blocked(page):
        input("LinkedIn wants a login/verification. Complete it in the window, then press Enter... ")
        page.goto(url)
        page.wait_for_timeout(4000)
        if blocked(page):
            sys.exit("Still blocked by a login/challenge. Stopping; I won't retry or bypass it.")


def main():
    if LAST_RUN.exists() and "--force" not in sys.argv and time.time() - LAST_RUN.stat().st_mtime < MIN_GAP_H * 3600:
        sys.exit(f"Already ran in the last {MIN_GAP_H}h. Use --force to override (not recommended).")
    from playwright.sync_api import sync_playwright
    today, found = date.today().isoformat(), []
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(".browser-profile", headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        for slug, game in GAMES.items():
            load(page, f"https://www.linkedin.com/games/{slug}/results/")
            btn = page.get_by_role("button", name="See full leaderboard")
            if not btn.count():
                print(f"{game}: no leaderboard button (not played today?), skipping")
            else:
                time.sleep(random.uniform(5, 15))
                btn.first.click()
                page.wait_for_timeout(4000)
                if blocked(page):
                    sys.exit("Blocked by a login/challenge after opening the leaderboard. Stopping.")
                try:
                    rows = scroll_rows(page)
                except ValueError as e:
                    sys.exit(f"{game}: {e}. Parser needs a fix; nothing written.")
                if not rows:
                    sys.exit(f"{game}: leaderboard parsed to zero rows. Page layout may have changed; nothing written.")
                found += [{"date": today, "game": game, "player": n, "timeSeconds": s, "hints": h} for n, s, h in rows]
                print(f"{game}: {len(rows)} scores")
            time.sleep(random.uniform(5, 15))
        ctx.close()
    if not found:
        sys.exit("No scores found for any game; data.json untouched.")
    print("\nAbout to save (compare with the leaderboards before publishing):")
    for r in found:
        print(f"  {r['game']:<12} {r['player']:<22} {r['timeSeconds'] // 60}:{r['timeSeconds'] % 60:02d}  hints={r['hints']}")
    shutil.copy("data.json", ".data.json.bak")
    d = json.load(open("data.json"))
    new = {(s["date"], s["game"], s["player"]) for s in found}
    d["scores"] = [s for s in d["scores"] if (s["date"], s["game"], s["player"]) not in new] + found
    d["updatedAt"] = datetime.now().astimezone().isoformat(timespec="minutes")
    json.dump(d, open("data.json", "w"), indent=1)
    if subprocess.run([sys.executable, "validate.py"]).returncode:
        shutil.copy(".data.json.bak", "data.json")
        sys.exit("Validation failed; data.json restored.")
    LAST_RUN.touch()


if __name__ == "__main__":
    main()

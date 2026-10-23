# Trackaholic, then and now

The story of [Trackaholic](https://trackaholic.app), from a nine-line terminal calculator in 2024 to the redesign shipped in October 2026, told through the screens of every version.

**Read it at [story.trackaholic.app](https://story.trackaholic.app).**

The app itself lives in [Abdulla1x/Trackaholic](https://github.com/Abdulla1x/Trackaholic).

## What's here

- `index.html`: the whole page, with no build step and no dependencies apart from Google Fonts.
- `media/<checkpoint>/<mobile|desktop>/`: full-page screenshots as WebP. `<page>.webp` is the page at 780 px (phone) or 1280 px (desktop); `<page>-2x.webp` is the desktop capture at 2560 px; `<page>-t.webp` is the small crop the strips show. The clips are H.264 MP4 with a `-poster.webp` frame.
- `media/2026-10g/<width>/looks/<screen>/<theme>-<palette>.webp`: Today, Progress and You in each of the app's twenty looks.

## Keeping it current

After every merge into Trackaholic's `main`, its `notify-story` workflow pings this repo, and `.github/workflows/sync.yml` runs two scripts:

- `scripts/sync_numbers.py` recounts the commits (facts row, chart and running total), merged pull requests and backend tests (rounded down to the hundred). If anything changed, it opens a pull request from `bot/recount`. Nothing goes live until that's merged. It only ever edits numbers, and it stops with an error if the text around a number has been reworded.
- `scripts/stale_check.py` keeps one issue labelled `story-sync` listing new features, new dated engineering notes in `docs/`, "Where it's going" cards that may need trimming, the waiting tags and the age of the last checkpoint. Closing the issue marks everything in it as handled; the next one starts after the last pull request it listed. Card keywords and what clears each tag live in `sync-config.json`.

Both can also be run by hand: Actions → Sync with Trackaholic → Run workflow, or locally with `--dry-run` for the issue.

Every screenshot and clip uses a demo account with made-up meals and weigh-ins. The exception is the July 2024 phone notes in "How it started", which are my own.

© Mohammad Abdullah. All rights reserved.

# HorizonXI Summoner Unlock Tracker

A local browser-based helper for the HorizonXI Summoner unlock quest **I Can Hear a Rainbow**.

The repository contains the full source and can be built into a single Windows EXE with PyInstaller.

## Repository layout

```text
src/
  weather_server.py
  Carbuncle_Rainbow_Tracker.html
HorizonXI_Summoner_Unlock_Tracker.spec
version_info.txt
requirements-build.txt
build_exe.bat
run_source.bat
.github/workflows/release.yml
```

## Run from source

Python 3 is required. No third-party runtime modules are needed.

From Windows CMD:

```bat
run_source.bat
```

or:

```bat
py -3 src\weather_server.py
```

The local server opens the tracker in your default browser.

## Build the Windows EXE

The easiest method is:

```bat
build_exe.bat
```

This creates a local virtual environment, installs PyInstaller, and builds:

```text
dist\HorizonXI_Summoner_Unlock_Tracker.exe
```

The EXE contains the HTML file. Python is not required on the machine that runs the built EXE.

### Manual build commands

From Windows CMD in the repository root:

```bat
py -3 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt
python -m PyInstaller --noconfirm --clean HorizonXI_Summoner_Unlock_Tracker.spec
```

## Put the source on GitHub from CMD

Install Git and GitHub CLI if needed:

```bat
winget install --id Git.Git -e
winget install --id GitHub.cli -e
```

Open a new CMD after installation, then authenticate:

```bat
gh auth login
```

In the project directory:

```bat
git init
git add .
git commit -m "Initial release"
git branch -M main
gh repo create HorizonXI-Summoner-Unlock-Tracker --public --source=. --remote=origin --push
```

If you already created an empty repository on GitHub instead, use:

```bat
git init
git add .
git commit -m "Initial release"
git branch -M main
git remote add origin https://github.com/YOUR_GITHUB_NAME/HorizonXI-Summoner-Unlock-Tracker.git
git push -u origin main
```

## Build locally and publish the EXE as a GitHub Release

First build:

```bat
build_exe.bat
```

Commit and push any source changes:

```bat
git add .
git commit -m "Release v24.0.0"
git push
```

Create and push the version tag:

```bat
git tag v24.0.0
git push origin v24.0.0
```

Then create the Release and upload the EXE with GitHub CLI:

```bat
gh release create v24.0.0 "dist\HorizonXI_Summoner_Unlock_Tracker.exe" --title "v24.0.0" --generate-notes
```

To replace an EXE already attached to that Release:

```bat
gh release upload v24.0.0 "dist\HorizonXI_Summoner_Unlock_Tracker.exe" --clobber
```

To inspect releases:

```bat
gh release list
gh release view v24.0.0
```

## Automatic GitHub build/release

This repository also contains:

```text
.github/workflows/release.yml
```

When you push a tag beginning with `v`, GitHub Actions builds the EXE on a Windows runner and creates/uploads the GitHub Release automatically.

Example:

```bat
git add .
git commit -m "Release v24.0.0"
git push
git tag v24.0.0
git push origin v24.0.0
```

With the workflow enabled, you do **not** need to run `gh release create` manually.

## Updating the version

For a new release, update the version in:

- `src/weather_server.py`
- the visible version badge in `src/Carbuncle_Rainbow_Tracker.html`
- `version_info.txt`

Then build/test and tag the matching version.

## Runtime data

When running from source, the map cache is stored in the repository `_cache` folder.

When running the one-file EXE, writable cache data is stored under:

```text
%LOCALAPPDATA%\HorizonXI_Summoner_Unlock_Tracker\_cache
```

This avoids trying to write into PyInstaller's temporary one-file extraction directory.


## v16 alert sounds

The weather watcher now has five built-in notification sounds:

- Crystal Chime
- Beacon
- Bell
- Ascending
- Urgent

The sounds are synthesized with the browser Web Audio API, so there are no
external audio files to package. The selected sound is saved in browser
localStorage.

Use **Test sound** to preview the currently selected sound. Testing works even
when **Sound alert** is unchecked; actual forecast alerts still respect the
Sound alert toggle.


## v17 future weather forecast

A separate **Next 7/14/21/28 Vana'diel Days** box is displayed below the current-day
weather opportunities.

It reads offsets +1 through +7 from the same per-zone Horizon weather forecast
response used for today's scan. No additional zone requests are required.

The future box:
- hides colors already marked obtained
- shows every eligible tracked zone
- ranks the best travel access first when multiple zones can satisfy one color
- shows the current forecast chance
- groups opportunities by Vana day
- continuously shows when each future Vana day starts in Earth time

Seven Vana'diel days cover about 6 hours 43 minutes of real time.
Future forecasts do not trigger notifications; alerts remain tied to current-day
actionable weather.


## v18 critical UI startup fix

v17 had a JavaScript initialization-order bug. The page checked
`ALERT_SOUND_PATTERNS` before the `const ALERT_SOUND_PATTERNS` declaration had
been initialized. JavaScript throws a ReferenceError in that situation.

Because the exception happened during initial page setup, later event handlers
were never installed. This made several unrelated controls appear dead at once,
including:
- Scan Horizon forecasts
- Enable browser notifications
- Test sound

v18 removes the early reference and validates the saved sound name without
touching the later constant.

Audio initialization is also more robust: the browser AudioContext is resumed
and awaited before tones are scheduled.


## v19 Wiki-anchored weather timing

Weather timing no longer relies on an independently reconstructed Vana'diel
midnight for forecast scheduling.

After each scan, v19 reads the Horizon Wiki **Today** row's `Earth Time` and
uses it as the timing anchor. The future Day +1 through Day +7 start times,
Today's forecast rollover countdown, and automatic rescan time are derived from
that same anchor.

The local helper can receive the Wiki's wall-clock text in a server/anonymous
timezone rather than the browser timezone. To avoid hard-coding any timezone or
DST rule, the browser tests nearby whole-hour interpretations of the Today
timestamp and selects the one that puts the Today start inside the current
57m36s Vana'diel-day window.

This makes the schedule DST-safe and user-timezone-neutral. If the Wiki Earth
Time cannot be parsed or reconciled, the tracker explicitly falls back to the
standard Vana epoch calculation.

Future cards now also display their local Earth start time next to the
countdown.


## v20: Align timeline rows with the Horizon Wiki

A previous attempt reconstructed the future forecast times by adding 57m36s
to the Today row, and tried arbitrary whole-hour timezone shifts. This made
the displayed time difficult to compare with the Wiki's individual rows.

Now each future day shows **that precise Wiki row's Earth Time**. The next-7
days box includes a visible Wiki Today (offset 0) reference, using Buburimu
Peninsula when available. Day +1 means the Wiki offset-1 row, not Today.
The browser parses the Wiki's `08-Oct 11:14 AM` format as local time, supports
year-end rollover, and uses that same row for the countdown. If an Earth
Time cannot be parsed, the raw Wiki text is still shown and the countdown
is marked unavailable rather than inventing a time. No guessed timezone or
Vana-day shift is applied. The auto-rescan follows the next upcoming forecast
row; if timing data is unavailable it retries after three minutes.

The Wiki may change how it renders time in future; if the anonymous helper
receives a different wall-clock timezone than the browser-facing website, the
raw times will need to be checked.


## v21: future-only weather forecasts

- Reads source day offsets 0–14 when the Wiki provides them; no extra HTTP requests.
- Separates original Wiki offsets from relative upcoming order.
- Displays the next **seven actual future timestamps** instead of always showing Wiki offsets +1 through +7.
- Past timestamps never appear as upcoming opportunities.
- The future cards update automatically when a timestamp passes, even if automatic network rescanning is off.
- Wiki times are shown unchanged, with no guessed timezone correction.
- If fewer than seven future rows are available from the source, shows only the available rows and explains why.


## v22: UTC -> browser timezone fix

The standalone Python helper downloads the Wiki's raw weather forecast HTML,
which does not execute the Wiki's client-side local-time conversion. The
`Earth Time` field from that HTML is interpreted as UTC, not as browser-local
time. Python returns `earth_unix_ms` for each offset 0..14 (and preserves the
original `earth_time` UTC text). The browser formats the timestamp in the
visitor's timezone with automatic daylight-saving handling. The Today reference
now shows both the converted local time and raw UTC value. Countdowns, future
row expiration, and automatic scan scheduling use the identical UTC timestamp.

**No fixed CET/CEST or numeric +/- hour patch is applied.**

GitHub Actions runs the Python UTC time regression tests and Node browser time
tests before building the EXE.


## v23 future forecast range selector

The future forecast box offers **7, 14, 21, or 28 upcoming Vana'diel days**
(default 7). The selected range is saved in browser localStorage and changing
it re-renders the most recently fetched forecast without making new requests.
The displayed IRL span is computed using 57m36s per Vana day.

The local Python parser accepts source offsets up to **+36**, allowing space
for expired day rows even with a 28-day selection. The extension can return
fewer rows than requested; the tracker shows the actual number available and
never extrapolates weather beyond what the Wiki returned. This is particularly
relevant for 21- or 28-day selections, since public Wiki examples commonly
include forecasts only through +15.

Weather time conversion and automatic rescan logic are unchanged from v22.


## v24 — selectable display timezone and timing diagnostics

The forecast displays exact UTC instants formatted in the selected IANA timezone.
A new **Display timezone** dropdown offers Browser (automatic), Europe/Madrid,
other common zones, and a custom IANA timezone identifier. In particular,
Europe/Madrid provides CEST (+02:00) or CET (+01:00) as appropriate for the
forecast date; do not manually add an offset to the Unix timestamp.

The reference below the future forecast reports the browser's actual timezone,
the selected display timezone, the raw Wiki Earth Time, the UTC timestamp,
and the displayed local time. This makes it possible to diagnose a browser
configured to UTC when the expected display is UTC+2. The display selector is
saved in localStorage.

Timezone selection never modifies timestamp arithmetic or forecast-day
ordering. Countdown durations and expiration filtering always use absolute
Unix epoch timestamps. If the Wiki source itself is inconsistent, the
diagnostics will expose that; do not compensate by silently shifting forecasts.

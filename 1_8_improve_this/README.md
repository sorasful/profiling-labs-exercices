# 1.8 - Improve this

`main.py` downloads the Open Food Facts delta files, parses them and imports the
products into a SQLite database. It works, but it is slow. Your job: profile it,
find the bottlenecks, and make it faster.

## Setup: run against a local mirror

The scripts in this exercise hit `http://localhost:8017` instead of the real
Open Food Facts servers. One helper script makes that work:

- ` run_me_first.py` downloads the delta files from Open Food Facts into
  `delta_cache/` (skipping anything already downloaded), then serves that
  folder on `http://localhost:8017`.

```bash
uv run python run_me_first.py   # keep running in one terminal
uv run python main.py           # the script under test, in another terminal
```

Restarting `run_me_first.py` is cheap: files already in `delta_cache/` are
never re-downloaded, it goes straight to serving.

## Why a local mirror?

1. **Reproducible measurements.** When you profile or benchmark, you want the
   numbers to reflect *your code*, not the internet. Real network latency and
   bandwidth vary from one run to the next (and from one machine to another),
   which makes it impossible to tell whether your optimization actually helped.
   Serving the files from localhost makes runs stable and comparable.
2. **No rate limiting.** Optimizing is an iterative process: you will run the
   script dozens of times. Open Food Facts rate-limits aggressive clients
   (HTTP 429), which would slow you down and skew your measurements.
3. **Be a good citizen.** There is no reason to re-download the same ~90 MB of
   data from a free, community-run service on every single run. Download once,
   replay locally as many times as you want.

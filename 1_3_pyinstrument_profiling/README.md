# 1_3: Let's start Profiling together

A deliberately naive scraper: it downloads a big JSON document hosted on this
repo (via raw.githubusercontent.com), extracts the image links from its content  
with a regex, then downloads every image into `images/`.


## Setup

```bash
uv sync
```

## Run

```bash
uv run main.py
```

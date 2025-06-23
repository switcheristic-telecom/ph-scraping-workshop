# Case study: Building a dataset of banner ads appearing on popular Japanese-language websites

In the rest of this lesson, we are going to build a dataset of banner ads appearing on popular Japanese-language websites in the year 2000 by scraping the Wayback Machine. Such a dataset can be of help for researchers in a number of areas - for example, researchers in digital marketing history may want to analyze early web advertising strategies, while researchers interested in the history of the ad network industry may want to observe the evolution of banner ad formats and targeting practices during the early commercialization of the internet.

## Download the lesson materials

Before we begin, you'll need to download the supporting files for this lesson. These include the curated list of Japanese websites from 2000, all the Python scripts we'll be using, and some helper data files.

Download the lesson files here: [TODO: lesson-files.zip](lesson-files.zip)

Extract the zip file to create your project directory. The archive contains:

- `nikkeibp-may2000.csv` Curated list of top Japanese websites from May 2000
- `requirements.txt` - Python dependencies needed for this lesson
- `iab-banner-ad-dimensions.csv` - Standard banner ad sizes from the Internet Advertising Bureau
- `jiaa-banner-ad-dimensions.csv` - Banner ad sizes from the Japan Interactive Advertising Association
- `1-query-cdx.py` - Query the Wayback Machine for available snapshots
- `2-download-snapshot.py` - Download the actual web pages
- `3-detect-frame-tags.py` - Detect nested pages in HTML `<frame>` tags
- `4-download-frames.py` - Download all detected frames
- `5-detect-image-tags.py` - Detect images from the all downloaded website and frames
- `6-download-banner-ads.py` - Download images that are likely to be banner ads
- `7-summarize-banner-ads.py` - Summarize the banner ads
- `util.py` - Shared utility functions
- `README.md` - Additional instructions

## Setting up the environment

Now that you have the lesson materials, let's install the necessary Python dependencies:

```bash
pip install -r requirements.txt
```

The scripts are organized in a logical sequence that mirrors our research workflow. Each script handles a specific part of the process, making it easy to understand what's happening at each step and to resume work if needed. We'll walk through each script in order, explaining what it does and how the techniques can be applied to other research questions.

## Building a list of historical URLs to scrape

For our study, we need a representative sample of popular Japanese websites from 2000. Fortunately, the business magazine Nikkei published a list of the top 50 most visited websites in Japan in May 2000, which has been preserved in [this academic paper](https://firstmonday.org/ojs/index.php/fm/article/view/802) studying early internet adoption in Japan.

The basic list looks like this:

```csv
rank,website
1,yahoo.co.jp
2,microsoft.com
```

### Refining our dataset

To make our analysis more focused, we've enhanced the original list by adding two important classifications: whether each site was primarily in Japanese, and what category of website it represented. We determined these by actually examining Wayback Machine snapshots from 2000 - a good reminder that historical web research often requires this kind of detective work to understand what sites were really like in their original context.

```csv
# nikkeibp-may2000.csv
rank,website,is_japanese,category
1,yahoo.co.jp,true,portal
2,microsoft.com,false,corporate
```

We've categorized sites using the same scheme as the original Nikkei study: `portal` (web directories and search engines), `content` (news, entertainment), `services` (web-based tools), `ISP` (internet service providers), `shopping` (e-commerce), and `corporate` (company websites).

For this lesson, we'll focus specifically on Japanese-language websites in the `portal` and `content` categories. These types of sites were most likely to feature banner advertising, since they relied on attracting large audiences and generating revenue through ads. This gives us 16 websites to examine - a manageable number for learning purposes while still providing enough data for meaningful analysis.

## Querying for website snapshots from the Wayback Machine

Now that we have our list of target websites, we need to find out what archived snapshots the Wayback Machine has available for each site from May 2000.

### Reading the list of websites

Let's start by examining how we load our curated list of Japanese websites. Open `1-query-cdx.py` and look at the first section:

```python
# 1-query-cdx.py (part 1)

import csv

CATEGORY_OF_INTEREST = ["portal", "content"]

japanese_websites = []
with open("nikkeibp-may2000.csv", "r") as file:
    reader = csv.DictReader(file)
    for row in reader:
        if (
            row.get("is_japanese") == "true"
            and row.get("category") in CATEGORY_OF_INTEREST
        ):
            japanese_websites.append(row["website"])

print(f"Found {len(japanese_websites)} Japanese websites to scrape")
```

### Working with the CDX API

The Wayback Machine's CDX (Crawl inDeX) API is our gateway to finding archived content. Think of it as a catalog that tells us exactly what snapshots are available for any given website and when they were captured. For each website in our list, we'll query the API to find all snapshots taken during May 2000.

Let's examine the helper functions in `util.py` that make working with the API easier:

```python
# util.py (part 1)

import requests, time, tenacity

retry = tenacity.retry(
    stop=tenacity.stop_after_attempt(10),
    wait=tenacity.wait_exponential(multiplier=1, min=2, max=32),
    after=lambda _: time.sleep(2),
)

def parse_wm_cdx_api_response_str(response_str: str) -> list[dict]:
    """Parse the response from the Wayback Machine CDX API"""
    rows = [entry for entry in response_str.strip().split("\n") if entry != ""]
    result = []
    for row in rows:
        fields = row.split(" ")
        result.append(
            {
                "urlkey": fields[0],
                "timestamp": fields[1],
                "original": fields[2],
                "mimetype": fields[3],
                "statuscode": fields[4],
                "digest": fields[5],
                "length": fields[6],
            }
        )
    return result

@retry
def query_wm_cdx_entries(
    url: str,
    from_time: str = "20000501000000",
    to_time: str = "20000531235959",
):
    """Query the Wayback Machine CDX API for a given URL and time range"""
    cdx_url = f"https://web.archive.org/cdx/search/cdx?url={url}&from={from_time}&to={to_time}"

    response = requests.get(cdx_url, timeout=30)
    response.raise_for_status()

    return parse_wm_cdx_api_response_str(response.text)

```

The `@retry` decorator is particularly important here. The Wayback Machine, like many free public services, can sometimes be slow or temporarily unavailable. This decorator automatically retries failed requests up to 10 times with increasing delays between attempts, making our scraping more reliable without requiring us to manually handle every potential network hiccup.

### Querying and organizing our data

Now we can systematically query the CDX API for each website and organize the results. Let's look at the rest of `1-query-cdx.py`:

```python
# 1-query-cdx.py (part 2)

import os, json
import util


OUTPUT_DIR = "data"
os.makedirs(OUTPUT_DIR, exist_ok=True)


for website in japanese_websites:
    print(f"Querying CDX for {website}")

    website_dir = os.path.join(OUTPUT_DIR, website)
    if os.path.exists(website_dir):
        print(f"  Skipping - folder already exists")
        continue

    cdx_entries = util.query_wm_cdx_entries(website)

    print(f"  Found {len(cdx_entries)} CDX entries")
    os.makedirs(website_dir, exist_ok=True)

    # Create folder structure for all entries of this website
    if cdx_entries:
        for cdx_entry in cdx_entries:
            website_timestamp_dir = os.path.join(website_dir, cdx_entry["timestamp"])
            os.makedirs(website_timestamp_dir, exist_ok=True)

            cdx_entry_path = os.path.join(website_timestamp_dir, "cdx_entry.json")
            with open(cdx_entry_path, "w") as f:
                json.dump(cdx_entry, f, indent=2)

        print(f"  Created {len(cdx_entries)} snapshot entry folders")

```

This script creates a organized folder structure that mirrors how the Wayback Machine organizes its content. Each website gets its own folder, and within that, each snapshot gets a folder named with its timestamp. The `cdx_entry.json` file in each folder contains the metadata we'll need to actually download that snapshot later.

Run this script with:

```bash
python 1-query-cdx.py
```

The resulting structure looks like this:

```bash
data/                          # Main output directory
├── example.com/               # One directory per website
│   └── 20000510123456/        # Timestamp-based snapshot directories
│       ├── cdx_entry.json     # CDX metadata for this snapshot
```

This approach has several advantages:

- It's easy to navigate in the folder structure
- It allows us to resume our work if something goes wrong
- It makes it simple to focus on specific websites or time periods later

## Downloading the website snapshots

With our CDX metadata in hand, we can now download the actual archived web pages. This is where we'll encounter some of the unique challenges of working with historical web content.

### Reading our saved metadata

First, let's examine how we read back all the CDX entries we saved in the previous step. Look at this function in `util.py`:

```python
# util.py (part 2)
import os, json

OUTPUT_DIR = "data"

def get_saved_website_entries() -> dict:
    """Get all the saved website entries
    dict: {website: [cdx_entry, ...], website2: [cdx_entry, ...], ...}
    """
    all_website_entries = {}

    for website in os.listdir(OUTPUT_DIR):
        website_dir = os.path.join(OUTPUT_DIR, website)
        all_website_entries[website] = []

        for timestamp_dir in os.listdir(website_dir):
            if os.path.isdir(os.path.join(website_dir, timestamp_dir)):
                cdx_meta_path = os.path.join(
                    website_dir, timestamp_dir, "cdx_entry.json"
                )
                with open(cdx_meta_path, "r") as f:
                    cdx_entry = json.load(f)
                all_website_entries[website].append(cdx_entry)

    return all_website_entries
```

```python
#2-download-snapshot.py (part 1)

import util


all_website_entries = util.get_saved_website_entries()
```

### Handling downloads and text encoding

Now comes the tricky part: actually downloading the web pages and handling their text encoding correctly. Remember, we're dealing with Japanese websites from 2000, which used various character encoding schemes that were common before UTF-8 became the universal standard.

```python
# util.py (part 3)

@retry
def download_website_snapshot(cdx_entry: dict) -> dict:
    wayback_url = f"https://web.archive.org/web/{cdx_entry['timestamp']}id_/{cdx_entry['original']}"
    response = requests.get(wayback_url, timeout=30)
    response.raise_for_status()
    return {
        "digest": cdx_entry["digest"],
        "file": response.content,
        "encoding": response.apparent_encoding,
    }


def save_website_snapshot(snapshot: dict, save_dir: str):
    """Save a website snapshot (original and utf8 versions) and encoding information to a directory"""
    os.makedirs(save_dir, exist_ok=True)

    # Save main HTML file (original encoding)
    html_filename = f"{snapshot['digest']}.html"
    with open(os.path.join(save_dir, html_filename), "wb") as f:
        f.write(snapshot["file"])

    # Save decoded UTF-8 version of HTML
    decoded_content = snapshot["file"].decode(snapshot["encoding"], errors="replace")
    with open(
        os.path.join(save_dir, f"{snapshot['digest']}_utf8.html"), "w", encoding="utf-8"
    ) as f:
        f.write(decoded_content)

    # Save encoding information
    with open(os.path.join(save_dir, "encoding.txt"), "w") as f:
        f.write(snapshot["encoding"])

```

Notice several important details in this code:

- We use the `id_` flag in our Wayback Machine URL, which tells the archive to serve us the original HTML without modifying any URLs. This gives us the authentic historical content.
- We save each file using its "digest" (a unique fingerprint) as the filename. This helps us identify duplicate content later.
- We save both the original encoded version and a UTF-8 version of each file. Japanese websites from 2000 might use encodings like `Shift-JIS`, `EUC-JP`, or `ISO-2022-JP`, and having both versions ensures we can work with the content regardless of encoding issues.
- We also save the detected encoding to a separate file, which will be useful for debugging and analysis.

### Implementing smart caching

Here's where we encounter a key insight about web archives: many snapshots of the same website are actually identical, even if they were captured at different times. The Wayback Machine assigns each unique piece of content a "digest" - essentially a fingerprint that identifies identical content. We can use this to avoid downloading the same content multiple times, which is both more efficient and more respectful of the Wayback Machine's servers.

```python
# util.py (part 4)

def find_and_copy_cached_snapshot(cached_snapshot_dir: str, save_dir: str) -> bool:
    """Find and copy a cached snapshot to a directory if it exists. Return True if a snapshot was found and copied."""
    if os.path.exists(cached_snapshot_dir):
        for filename in os.listdir(cached_snapshot_dir):
            src = os.path.join(cached_snapshot_dir, filename)
            dst = os.path.join(save_dir, filename)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
                fdst.write(fsrc.read())
        return True
    return False
```

Now we can put it all together in our download script:

```python
# 2-download-snapshot.py (part 2)

OUTPUT_DIR = "data"
CACHE_DIR = "cache"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)


for website, entries in all_website_entries.items():
    print(f"Found {len(entries)} snapshots for {website}")

    # Download ALL entries for each website
    for cdx_entry in entries:
        snapshot_dir = os.path.join(OUTPUT_DIR, website, cdx_entry["timestamp"])

        # Check if snapshot has already been downloaded
        html_filename = f"{cdx_entry['digest']}.html"
        html_path = os.path.join(snapshot_dir, html_filename)

        if os.path.exists(html_path):
            print(f"  Skipping {cdx_entry['timestamp']} - already downloaded")
            continue

        # Check if snapshot has already been cached
        cache_snapshot_dir = os.path.join(CACHE_DIR, cdx_entry["digest"])
        if util.find_and_copy_cached_snapshot(cache_snapshot_dir, snapshot_dir):
            print(f"  Loaded from cache {cdx_entry['timestamp']}, skipping")
            continue

        print(f"  Downloading snapshot from {cdx_entry['timestamp']}")

        try:
            snapshot = util.download_website_snapshot(cdx_entry)
            util.save_website_snapshot(snapshot, snapshot_dir)
            util.save_website_snapshot(snapshot, cache_snapshot_dir)
            print(f"    Saved snapshot to {snapshot_dir}")
        except Exception as e:
            print(f"    Error downloading {cdx_entry['timestamp']}: {e}")
```

The cache directory organizes files by their digest (content fingerprint), making it easy to identify and reuse identical content across different timestamps and websites.

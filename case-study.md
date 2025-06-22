# Case study: Building a dataset of banner ads appearing on popular Japanese-language websites

In the rest of this lesson, we are going to build a dataset of banner ads appearing on popular Japanese-language websites in the year 2000 by scraping the Wayback Machine. Such a dataset can be of help for researchers in a number of areas - for example, researchers in , while researchers interested in the history of the ad network industry may want to observe

The challenge involved in building the dataset is not only technical but also

## Setting up the environment

Install the dependencies by running:

```bash
pip install -r requirements.txt
```

We will have a few different scripts in this lesson, you can go ahead and create these files:

- `1-query-cdx.py`
- `2-download-snapshot.py`
- `3-scrape-resources.py`
- `4-summarize-image-resources.py`
- `util.py`

## Building a list of historical URLs to scrape

For this lesson, we are going to use a list of top-50 most visited websites in Japan in May 2000, released by the Nikkei. The list is available in the [this paper](https://firstmonday.org/ojs/index.php/fm/article/view/802).

The list is available in the following format:

```csv
rank,website
1,yahoo.co.jp
2,microsoft.com
```

We further augment the list by adding `is_japanese` and `category` columns. To determine these classifications, we examined Wayback Machine snapshots from 2000 to observe each website's actual language and business model during that period. Categories follow the scheme from [the aforementioned paper](https://firstmonday.org/ojs/index.php/fm/article/view/802): `portal`, `content`, `services`, `ISP`, `shopping`, and `corporate`. Our category counts match the distributions reported in the original Nikkei study.

```csv
# nikkeibp-may2000.csv
rank,website,is_japanese,category
1,yahoo.co.jp,true,portal
2,microsoft.com,false,corporate
```

For this lesson, we are going to focus on Japanese-language websites in the `portal` and `content` categories.

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

## Querying CDX entries from the Wayback Machine

Using the Wayback Machine's CDX API, we can query all entries of a website given a URL and a time range. In this case study, we will focus on the May 2000 snapshot of the websites (from `20000501000000` to `20000531235959`).

Let's create some helper functions in `util.py` to handle interacting with the Wayback Machine. We'll add more helper functions to this file as we go along.

Here's the first set of functions to query the CDX entries for a website:

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

The `@retry` decorator above automatically retries failed function calls up to 10 times with exponential backoff, making our API requests more resilient to temporary network issues without cluttering the core logic. Feel free to adjust these retry parameters to match your needs.

Once we have the function, we can use it to query the CDX entries for a website. Let's create a script to do this.

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

We will save the CDX entries in a folder structure that mirrors the Wayback Machine's snapshot structure. The `cdx_entry.json` will guide us to the actual snapshot. Having intermediate files saved is also good as it allows us to resume the scraping process if it fails halfway through.

```bash
data/                          # Main output directory
├── example.com/               # One directory per website
│   └── 20000510123456/        # Timestamp-based snapshot directories
│       ├── cdx_entry.json     # CDX metadata for this snapshot
```

## Downloading the website snapshot

Since we have the CDX entries saved, we can read the `cdx_entry.json` file to get the timestamp and the digest of the snapshot. Let's create a script in `util.py` to do this.

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

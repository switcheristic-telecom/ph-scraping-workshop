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
- `banner-ads-summary-reference.csv` - Reference summary of the banner ads collection
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
    website_dir = os.path.join(OUTPUT_DIR, website)
    if os.path.exists(website_dir):
        continue

    cdx_entries = util.query_wm_cdx_entries(website)
    os.makedirs(website_dir, exist_ok=True)

    # Create folder structure for all entries of this website
    if cdx_entries:
        for cdx_entry in cdx_entries:
            website_timestamp_dir = os.path.join(website_dir, cdx_entry["timestamp"])
            os.makedirs(website_timestamp_dir, exist_ok=True)
            cdx_entry_path = os.path.join(website_timestamp_dir, "cdx_entry.json")
            with open(cdx_entry_path, "w") as f:
                json.dump(cdx_entry, f, indent=2)
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
def get_saved_website_entries() -> list[dict]:
    """Get all the saved website entries
    Returns a list of dicts with the following keys:
    - website: the website name
    - snapshot_dir: the directory of the website snapshot
    - cdx_entry: the CDX entry of the website
    """
    all_website_entries = []

    for website in os.listdir(OUTPUT_DIR):
        website_dir = os.path.join(OUTPUT_DIR, website)

        for timestamp_dir in os.listdir(website_dir):
            if os.path.isdir(os.path.join(website_dir, timestamp_dir)):
                website_snapshot_dir = os.path.join(website_dir, timestamp_dir)
                cdx_meta_path = os.path.join(website_snapshot_dir, "cdx_entry.json")
                with open(cdx_meta_path, "r") as f:
                    cdx_entry = json.load(f)
                all_website_entries.append(
                    {
                        "website": website,
                        "snapshot_dir": website_snapshot_dir,
                        "cdx_entry": cdx_entry,
                    }
                )

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
        files = os.listdir(cached_snapshot_dir)
        # If no files, return False
        if not files:
            return False
        for filename in files:
            src = os.path.join(cached_snapshot_dir, filename)
            dst = os.path.join(save_dir, filename)
            # If file already exists, copy it to the save_dir
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
                fdst.write(fsrc.read())
        return True
    return False

```

Now we can put it all together in our download script:

```python
# 2-download-snapshot.py (part 2)

for entry in all_website_entries:
    snapshot_dir = entry["snapshot_dir"]
    cdx_entry = entry["cdx_entry"]

    # Check if snapshot has already been downloaded
    html_filename = f"{cdx_entry['digest']}.html"
    html_path = os.path.join(snapshot_dir, html_filename)

    if os.path.exists(html_path):
        continue

    # Check if snapshot has already been cached
    cache_snapshot_dir = os.path.join(CACHE_DIR, cdx_entry["digest"])
    if util.find_and_copy_cached_snapshot(cache_snapshot_dir, snapshot_dir):
        continue

    try:
        snapshot = util.download_website_snapshot(cdx_entry)
        util.save_website_snapshot(snapshot, snapshot_dir)
        util.save_website_snapshot(snapshot, cache_snapshot_dir)
    except Exception as e:
        print(f"Error downloading {cdx_entry['timestamp']}: {e}")
```

The cache directory organizes files by their digest (content fingerprint), making it easy to identify and reuse identical content across different timestamps and websites.

Run the script with:

```bash
python 2-download-snapshot.py
```

The folder structure now includes the downloaded snapshot files:

```bash
data/
├── example.com/
│   └── 20000510123456/
│       ├── ...
│       ├── IU5AG2DC5GK33ALX3VFXLUEAIHRTCDQF.html # Original HTML file
│       ├── IU5AG2DC5GK33ALX3VFXLUEAIHRTCDQF_utf8.html # UTF-8 encoded HTML file
│       ├── encoding.txt       # Encoding information
```

## Detecting nested pages in HTML `<frame>` tags

Now that we've downloaded the website snapshots, we can start looking for nested pages in the HTML `<frame>` tags.

### Using BeautifulSoup to parse the HTML and find the `<frame>` tags

[TO WRITE: we are using bs4 to parse the HTML and find the `<frame>` tags] [TO WRITE: note that the file we read in is the utf8 version, not the original encoding] [TO WRITE: explain the downbelow code snippet]

```python
# util.py (part 5)
from bs4 import BeautifulSoup
def detect_and_save_frame_tag_attrs(
    soup: BeautifulSoup,
    website_dir: str,
) -> list[dict]:
    """Find all frame tag with their attribute and return a list of dicts"""
    all_frame_tags = soup.find_all("frame")
    frame_tag_attrs = [frame.attrs for frame in all_frame_tags]
    with open(os.path.join(website_dir, "frame_tags.json"), "w") as f:
        json.dump(frame_tag_attrs, f)
    return frame_tag_attrs
```

[TO WRITE: explain the downbelow code snippet]

```python
# 3-detect-frame-tags.py
for entry in all_website_entries:
    website = entry["website"]
    snapshot_dir = entry["snapshot_dir"]
    cdx_entry = entry["cdx_entry"]

    # Check if snapshot has already been downloaded
    utf8_html_filename = f"{cdx_entry['digest']}_utf8.html"
    utf8_html_path = os.path.join(snapshot_dir, utf8_html_filename)

    if not os.path.exists(utf8_html_path):
        continue

    with open(utf8_html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
        util.detect_and_save_frame_tag_attrs(soup, snapshot_dir)
```

Run the script with:

```bash
python 3-detect-frame-tags.py
```

The resulting structure looks like this:

```bash
data/
├── example.com/
│   └── 20000510123456/
│       ├── ...
│       ├── frame_tags.json
```

[TO WRITE: In our dataset, `nikkeibp.co.jp` and `nikkei.co.jp` are the only two websites using `<frame>` tags to display banner ads, but it's good to include them, otherwise the original html doesn't tell us anything about the actual content of the website]

## Downloading the detected frames

### Retrieving the frame tags

Similar to the `2-download-snapshot.py` script, we will write a helper function to retrieve the frame tags from the `frame_tags.json` file.

```python
# util.py (part 6)
def get_saved_frame_tags_with_parent_info() -> list[dict]:
    all_frame_tags = []
    all_website_entries = get_saved_website_entries()
    for entry in all_website_entries:
        website = entry["website"]
        website_dir = entry["snapshot_dir"]
        cdx_entry = entry["cdx_entry"]
        frame_tags_path = os.path.join(website_dir, "frame_tags.json")
        try:
            with open(frame_tags_path, "r") as f:
                frame_tags = json.load(f)
                frame_tags_with_dir = [
                    {
                        "website_dir": website_dir,
                        "website": website,
                        "parent_cdx_entry": cdx_entry,
                        "frame_tags": frame_tag,
                    }
                    for frame_tag in frame_tags
                ]
                all_frame_tags.extend(frame_tags_with_dir)
        except Exception as e:
            continue
    return all_frame_tags
```

### Designing the folder structure for the detected frames

[TO WRITE: we are putting the detected frames into folder under the parent website folder, eg `data/nikkeibp.co.jp/20000510123456/frames/[frame_tag_src]`]. The `frame_tag_src` is the `src` attribute of the `<frame>` tag. Yet, they are not good folder names because they contain special characters and spaces. We will use the `url_to_filename` function to convert them into safe filenames.

```python
# util.py (part 7)
def url_to_filename(url: str) -> str:
    # Remove protocol and split on slashes
    url = url.split("://")[-1].replace("/", "_")
    # Replace any remaining invalid characters with underscores
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in url)
```

### Querying the CDX API for the closest snapshot entry

Similar to downloading the original website snapshot, we will query the CDX API for each frame tag to find the closest snapshot entry. We limit the number of results to 1 (this also makes the query faster) and sort by the closest timestamp. [TO WRITE: talk about time skew]

```python
# util.py (part 8)

@retry
def query_wm_cdx_closest_entry(url: str, timestamp: str) -> dict | None:
    cdx_url = f"https://web.archive.org/cdx/search/cdx?limit=1&sort=closest&url={url}&closest={timestamp}"
    response = requests.get(cdx_url, timeout=30)
    response.raise_for_status()
    entries = parse_wm_cdx_api_response_str(response.text)
    return entries[0] if entries else None
```

### Implementing the frame downloading

[TO WRITE: we are using similar strategy as the download code for the original website snapshot, putting downloaded results into a cache folder] [TO WRITE:] [TO WRITE: The code is very verbose so we won't include it here, but you can find it in the `4-download-frames.py` script] [TO WRITE: Downbelow is a psuedo code for the download code]

```python
# 4-download-frames.py (pseudo code)
for frame_tag_with_parent_info in all_frame_tags_with_parent_info:
    # If frame tag src is a full URL, use it as is, else join with original URL
    actual_frame_url = piece_together_actual_url(frame_tag_src_url, parent_url)
    frame_cdx_entry = query_wm_cdx_closest_entry(actual_frame_url, parent_timestamp)
    if frame_cdx_entry and frame_cdx_entry["statuscode"] == "200":
      if file_exists:
         continue
      else if cached:
          find_and_copy_cached_snapshot(frame_cdx_entry["digest"], frame_snapshot_dir)
      else:
        frame_snapshot = download_website_snapshot(frame_cdx_entry)
        save_website_snapshot(frame_snapshot, frame_snapshot_dir)
        save_website_snapshot(frame_snapshot, cache_snapshot_dir)
```

Run the script with:

```bash
python 4-download-frames.py
```

The resulting structure looks like this:

```bash
data/
├── example.com/
│   └── 20000510123456/
│       ├── ...
│       ├── frames/
│       │   ├── ...
│       │   ├── frame_url_1/
│       │       ├── ...
│       │       ├── cdx_entry.json # cdx entry of the frame
│       │       ├── encoding.txt # encoding of the frame
│       │       ├── [FRAME_DIGEST].html # original html file of the frame
│       │       ├── [FRAME_DIGEST]_utf8.html # utf8 encoded html file of the frame
```

## Detecting image assets in HTML `<img>` tags

Now we have both the original website snapshot and the nested frames. We can start looking for image assets in the `<img>` tags in all the html files.

### Retrieving the original website and frame entries

[TO WRITE: similarly, we will write a helper function to retrieve the original website and frame entries with adequate metadata] [TO WRITE: the function is very similar to the one for retrieving the frame tags, we will only show the api spec here]

```python
# util.py (part 9 - api spec)
def get_saved_website_and_frame_entries() -> list[dict]:
    """Get all the saved frame tags for a given website directory
    Returns a list of dicts with the following keys:
    - website_dir: the directory of the website
    - website: the website name
    - cdx_entry: the CDX entry of the website
    - type: "website" or "frame"
    """

```

### Using BeautifulSoup to parse the HTML and find the `<img>` tags

[TO WRITE: we are using the same strategy as the frame detection, but this time we are looking for the `<img>` tags] [TO WRITE: one thing we are doing differently is that we are also looking for the link in the wrapping `<a>` tags for the `<img>` tags, because most banner ads are wrapped in `<a>` tags to go somewhere when clicked]

```python
# util.py (part 10)
import urllib.parse

def detect_and_save_image_tag_attrs(
    soup: BeautifulSoup, website_dir: str, parent_cdx_entry: dict
) -> list[dict]:
    image_tags = []
    for img in soup.find_all("img"):
        image_tag_attrs = img.attrs
        if img.parent.name == "a":
            image_tag_attrs["parent_href"] = img.parent["href"]
            if img.parent["href"].startswith("http"):
                image_tag_attrs["full_parent_href"] = img.parent["href"]
            else:
                image_tag_attrs["full_parent_href"] = urllib.parse.urljoin(
                    parent_cdx_entry["original"], img.parent["href"]
                )
        image_tags.append(image_tag_attrs)
    with open(os.path.join(website_dir, "image_tags.json"), "w") as f:
        json.dump(image_tags, f)

    return image_tags
```

### Detect for all the images in the website

[TO WRITE: Same drill, we run the detect function for every website and frame entry]

```python
# 5-detect-image-tags.py (simplified)
all_website_and_frame_entries = util.get_saved_website_and_frame_entries()

for entry in all_website_and_frame_entries:
    website = entry["website"]
    website_dir = entry["website_dir"]
    cdx_entry = entry["cdx_entry"]

    # Check if snapshot has already been downloaded
    utf8_html_filename = f"{cdx_entry['digest']}_utf8.html"
    utf8_html_path = os.path.join(website_dir, utf8_html_filename)

    if not os.path.exists(utf8_html_path):
        continue

    with open(utf8_html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
        image_tags = util.detect_and_save_image_tag_attrs(soup, website_dir, cdx_entry)
```

Run the script with:

```bash
python 5-detect-image-tags.py
```

The resulting structure looks like this:

```bash
data/
├── example.com/
│   └── 20000510123456/
│       ├── ...
│       ├── image_tags.json # image tags in the website
│       ├── frames/
│       │   ├── ...
│       │   ├── frame_url_1/
│       │       ├── ...
│       │       ├── image_tags.json # image tags in the frame
```

## Download images if the size fits the banner ad criteria

### Banner Ad Dimensions Detection

[TO WRITE: We source the `iab-banner-ad-dimensions.csv` from the `jiaa-banner-ad-dimensions` folder in the `data` folder from a Japanese book "図解 インターネット広告"] [TO WRITE: explain IAB is international, JIAA is Japanese] [TO WRITE: there is a function in `util.py` to check if the image size fits the banner ad criteria]

```python
# util.py (part 11 - api spec)
def check_banner_properties(width: int, height: int) -> dict:
    """Return the banner ad type if the width and height matches the banner ad criteria
    Returns a dict with the following keys:
    - iab_size: the IAB banner category (if fits)
    - jiaa_size: the JIAA banner category (if fits)
    - is_banner_ad: True if the width and height matches the banner ad criteria (either IAB or JIAA)
    """
    pass
```

### Retrieving the image tags with parent info

[TO WRITE: we are using the same strategy as the frame detection, but this time we are looking for the `<img>` tags] [TO WRITE: one thing we are doing differently is that we are also looking for the link in the wrapping `<a>` tags for the `<img>` tags, because most banner ads are wrapped in `<a>` tags to go somewhere when clicked]

```python
# util.py (part 12 - api spec)
def get_saved_image_tags_with_parent_info() -> list[dict]:
    """Get all the saved image tags for a given website directory
    Returns a list of dicts with the following keys:
    - website_dir: the directory of the website
    - website: the website name
    - cdx_entry: the CDX entry of the website
    - image_tag: the image tag
    """
```

### Downloading images recognized as banner ads

[TO WRITE: we will go through all the image tags with parent info, and if the image size (IMPORTANT: according to the image tag data, not the actual image file, we will come back to this in the final summary of banner ad collection) fits the banner ad criteria, we will download the image]. The utility code that powers this is in part 13 of `util.py`.

```python
# 6-download-banner-ads.py (pseudo code)
for image_tag_with_parent_info in all_image_tags_with_parent_info:
    if not tag_has_src_width_height(image_tag):
        continue
    if not is_img_tag_a_banner_ad(image_tag):
        continue
    image_cdx_entry = query_wm_cdx_closest_entry(image_tag_src, parent_timestamp)
    if image_cdx_entry and image_cdx_entry["statuscode"] == "200":
      if file_exists:
         continue
      else if cached:
          find_and_copy_cached_snapshot(image_cdx_entry["digest"], image_snapshot_dir)
      else:
        image_snapshot = download_image_snapshot(image_cdx_entry)
        save_image_snapshot(image_snapshot, image_snapshot_dir)
        save_image_snapshot(image_snapshot, cache_snapshot_dir)
        save_image_tag_attrs(image_snapshot_dir)
```

Run the script with:

```bash
python 6-download-banner-ads.py
```

The resulting structure looks like this:

```bash
data/
├── example.com/
│   └── 20000510123456/
│       ├── ...
│       ├── banners
│       │   ├── ...
│       │   ├── banners_url_1/
│       │   │   ├── ...
│       │   │   ├── [IMAGE_DIGEST].[ext]
│       │   │   ├── image_tag_attrs.json # image tag attributes
│       │   │   ├── cdx_entry.json # cdx entry of the image
```

## Summarizing the banner ad collection

[TO WRITE: we find all the images downloaded, and associate the banner ad images with the image tag parameters, the actual image metadata as we read it with PIL (there are some discrapencies between the image tag parameters and the actual image metadata, we will discuss this in the final summary of banner ad collection), and the cdx entry of the image, and the cdx entry of the parent website.]

### Read image metadata using PIL

[TO WRITE: we are using the `get_image_metadata` function in `util.py` to read the image metadata]

```python
# util.py (part 14 - api spec)
def get_image_metadata(image_path: str) -> dict:
    """Get the metadata of an image
    Returns a dict with the following keys:
    - width: the width of the image
    - height: the height of the image
    - size: the size of the image
    - animated: whether the image is animated
    - frame_count: the number of frames in the image
    - animation_duration: the duration of the animation
    - loop_count: the number of times the animation loops
    - iab_size: the IAB banner category (if fits)
    - jiaa_size: the JIAA banner category (if fits)
    - corrupt: whether the image is corrupt
    """
```

### Generating a spreadsheet summary

[TO WRITE: the spreadsheet field include]

- Parent website info
  - `website`: the parent website name
  - `website_timestamp`: the timestamp of the parent website
- Image CDX entry
  - `urlkey`: the urlkey of the image
  - `timestamp`: the timestamp of the image
  - `original`: the original url of the image
  - `mimetype`: the mimetype of the image
  - `statuscode`: the status code of the image
  - `digest`: the digest of the image
  - `length`: the length of the image
- Image metadata
  - `width`: the width of the image
  - `height`: the height of the image
  - `size`: the size of the image
  - `animated`: whether the image is animated
  - `frame_count`: the number of frames in the image
  - `animation_duration`: the duration of the animation
  - `loop_count`: the number of times the animation loops
  - `iab_size`: the IAB banner category (if fits)
  - `jiaa_size`: the JIAA banner category (if fits)
  - `corrupt`: whether the image is corrupt
- Image tag parameters
  - `image_tag_width`: the width of the image tag
  - `image_tag_height`: the height of the image tag
  - `image_tag_banner_iab_size`: the IAB banner category (if fits)
  - `image_tag_banner_jiaa_size`: the JIAA banner category (if fits)
  - `image_tag_parent_href`: the parent href of the image tag
  - `image_tag_full_parent_href`: the full parent href of the image tag
  - `image_tag_alt_text`: the alt text of the image tag
- Time skew
  - `time_skew`: the time skew between the image and the parent website in seconds

Example output:

| Field                      | Value                                                                                                                                                           |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| website                    | nikkeibp.co.jp                                                                                                                                                  |
| website_timestamp          | 20000511101011                                                                                                                                                  |
| urlkey                     | jp,co,nikkeibp,bizad)/image/ng_biztech/hitachisuperh991001.gif                                                                                                  |
| timestamp                  | 20000925212420                                                                                                                                                  |
| original                   | http://bizad.nikkeibp.co.jp:80/image/ng_biztech/hitachisuperh991001.gif                                                                                         |
| mimetype                   | im                                                                                                                                                              |
| statuscode                 | 200                                                                                                                                                             |
| digest                     | WGZQRI7HDFTA5CQ5BK4V2YYAZIXMHYWM                                                                                                                                |
| length                     | 10016                                                                                                                                                           |
| width                      | 468                                                                                                                                                             |
| height                     | 60                                                                                                                                                              |
| size                       | 9842                                                                                                                                                            |
| animated                   | True                                                                                                                                                            |
| frame_count                | 10                                                                                                                                                              |
| animation_duration         | 5000                                                                                                                                                            |
| loop_count                 | 0                                                                                                                                                               |
| iab_size                   | Full Banner                                                                                                                                                     |
| jiaa_size                  | Regular Banner                                                                                                                                                  |
| corrupt                    | False                                                                                                                                                           |
| time_skew                  | 11877249.0                                                                                                                                                      |
| image_tag_width            | 468                                                                                                                                                             |
| image_tag_height           | 60                                                                                                                                                              |
| image_tag_banner_iab_size  | Full Banner                                                                                                                                                     |
| image_tag_banner_jiaa_size | Regular Banner                                                                                                                                                  |
| image_tag_parent_href      | /event.ng/Type=click&ProfileID=62&RunID=1419&AdID=1419&GroupID=11&FamilyID=1&TagValues=263&Redirect=http:%2F%2Fwww.super-h.com%2F                               |
| image_tag_full_parent_href | http://bizad.nikkeibp.co.jp:80/event.ng/Type=click&ProfileID=62&RunID=1419&AdID=1419&GroupID=11&FamilyID=1&TagValues=263&Redirect=http:%2F%2Fwww.super-h.com%2F |
| image_tag_alt_text         | HITACHI Click Here!                                                                                                                                             |

The summary script is `7-summarize-banner-ads.py`. To

```bash
python 7-summarize-banner-ads.py
```

The output is `banner-ads-summary.csv`.

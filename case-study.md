# Case study: Building a dataset of banner ads appearing on popular Japanese-language websites

In the rest of this lesson, you will build a dataset of banner ads appearing on popular Japanese-language websites in the year 2000 by scraping the Wayback Machine. Such a dataset can help researchers in several areas, including researchers working on the history of web advertising, e-commerce, online visual culture, and web archiving. 



## Download the lesson materials

Before you begin, you will need to download the supporting files for this lesson. These include a curated list of popular Japanese websites from 2000, all the Python scripts you will be using, and some helper data files.

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

## Building a seed URL list to scrape

For our study, we need a sample of popular Japanese websites. The media company Nikkei BP published a list of the top 50 most visited websites by home users in Japan in May 2000, which has been preserved in a 2000 study about cultural differences in e-commerce between the United States and Japan [^PAPER]. We are going to use the list as the basis for scraping. Using archived , e further narrow our target down to 

## Downloading web pages
### Working with the CDX API
First, we will construct a utility function to query the Wayback Machine CDX Server API. The function 

We use the tenacity library to decorate our query_wm_cdx_entries function so that any transient failures (like timeouts or rate-limits) automatically trigger up to 10 retry attempts, with an exponential back-off wait (starting at 2 seconds, doubling each time up to 32 s) and an extra 2 seconds pause after each failed try.

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

### Querying and organizing our data

Now we can systematically query the CDX API for each website and organize the results. Observe the rest of `⁠1-query-cdx.py`:

```python
# 1-query-cdx.py (part 2)
OUTPUT_DIR = "data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

for website in japanese_websites:
    website_dir = os.path.join(OUTPUT_DIR, website)
    if os.path.exists(website_dir):
        continue

    cdx_entries = util.query_wm_cdx_entries(website)
    os.makedirs(website_dir, exist_ok=True)

    if cdx_entries:
        for cdx_entry in cdx_entries:
            website_timestamp_dir = os.path.join(website_dir, cdx_entry["timestamp"])
            os.makedirs(website_timestamp_dir, exist_ok=True)
            cdx_entry_path = os.path.join(website_timestamp_dir, "cdx_entry.json")
            with open(cdx_entry_path, "w") as f:
                json.dump(cdx_entry, f, indent=2)
```

This script creates an organized folder structure that mirrors how the Wayback Machine organizes its content. Each website gets its own folder, and within that, each snapshot gets a folder named with its timestamp. The `⁠cdx_entry.json` file in each folder contains the metadata you'll need to actually download that snapshot later.

Run the script with `python 1-query-cdx.py` and the resulting structure looks like this:

```bash
data/                          # Main output directory
├── example.com/               # One directory per website
│   └── 20000510123456/        # Timestamp-based snapshot directories
│       ├── cdx_entry.json     # CDX metadata for this snapshot
```

## Downloading the web page snapshots

With the CDX metadata in hand, we can now download the actual archived web pages. This is where we will encounter some of the unique challenges of working with historical web content.

### Retrieving saved metadata

First, examine how to read back all the CDX entries you saved in the previous step. Look at this function in `⁠util.py` that gathers all the information in a list of dicts. In the rest of the lesson, we will use many functions of such kind that gathers scraped data from the folder structure.

```python
# util.py (part 2)
def retrieve_saved_website_entries() -> list[dict]:
    """Retrieve all the saved website entries
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

Now we can use the function in `⁠2-download-snapshot.py`:

```python
#2-download-snapshot.py (part 1)
import util
all_website_entries = util.retrieve_saved_website_entries()
```

### Handling downloads and text encoding

To download website snapshot, we construct the URL using the `timestamp` and `original` fields of the CDX entry. Use the `⁠id_` flag to retrieve original HTML without replay modifications.

Also, as we are dealing with Japanese website before 2000, which used various character encoding schemes (eg `Shift-JIS`, `EUC-JP`, or `ISO-2022-JP`) that were common before UTF-8 became the universal standard, we will need to handle the text encoding correctly. We will save both the original encoded version and a UTF-8 version of each file for future use.

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

### Implementing smart caching

Many snapshots of the same URL are actually identical, even though they were captured at different times. We can use the `digest` column in the CDX data to avoid downloading the same content multiple times, which is both more efficient and more respectful of the Wayback Machine's servers.

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
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

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

The `cache` directory organizes files by their `digest`, making it easy to identify and reuse identical content across different timestamps and websites.

Run the script with `python 2-download-snapshot.py` and the `data` folder now includes the downloaded snapshot files:

```bash
data/
├── example.com/
│   └── 20000510123456/
│       ├── ...
│       ├── IU5AG2DC5GK33ALX3VFXLUEAIHRTCDQF.html # Original HTML file
│       ├── IU5AG2DC5GK33ALX3VFXLUEAIHRTCDQF_utf8.html # UTF-8 encoded HTML file
│       ├── encoding.txt       # Encoding information
```

## Detecting nested pages in HTML frame tags

Now that we have downloaded the website snapshots, we can start looking for nested pages in the HTML `⁠<frame>` tags.

### Using BeautifulSoup to parse the HTML and find frame tags

We will use BeautifulSoup to parse the HTML and extract frame information. We use the `⁠find_all` method to find all the `⁠<frame>` tags, and then save the attributes of each tag to a `⁠frame_tags.json` file.

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

The main detection script iterates through all downloaded website snapshots. Note that we read the UTF-8 version of the files, not the original encoding.

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

Run the script with `python 3-detect-frame-tags.py` and each website folder now includes the `frame_tags.json` file.

```bash
data/
├── example.com/
│   └── 20000510123456/
│       ├── ...
│       ├── frame_tags.json
```

In our dataset, ⁠`nikkeibp.co.jp` and ⁠`nikkei.co.jp` are the only two websites using ⁠`<frame>` tags to display banner ads. While not all sites use frames, it is important to include them because the original HTML does not reveal the actual content of the website if the main content is loaded through frames.

## Downloading the detected frames

We will now download the frame content that was detected in the previous step.

### Retrieving the frame tags

Similar to the `⁠2-download-snapshot.py` script, we will write a retrieve function to load the existing `⁠frame_tags.json` files:

```python
# util.py (part 6 - api spec)
def retrieve_saved_frame_tags_with_parent_info() -> list[dict]:
    """Retrieve all the saved frame tags for a given website directory
    Returns a list of dicts with the following keys:
    - website_dir: the directory of the website
    - website: the website name
    - cdx_entry: the CDX entry of the website
    - frame_tag: the frame tag
    """

```

### Designing the folder structure for the detected frames

We will put the detected frames into folders under the parent website folder, e.g., `⁠data/nikkeibp.co.jp/20000510123456/frames/[frame_tag_src]`. The `⁠frame_tag_src` is the `⁠src` attribute of the `⁠<frame>` tag. However, these aren't good folder names because they could contain special characters, such as `/` and spaces. We will use the `⁠url_to_filename` function to convert them into safe filenames.

```python
# util.py (part 7)
def url_to_filename(url: str) -> str:
    url = url.split("://")[-1].replace("/", "_")
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in url)
```

### Querying the CDX API for the closest snapshot entry

Similar to downloading the original website snapshot, we will query the CDX API for each frame tag to find the closest snapshot entry. We limit the number of results to 1 (this also makes the query faster), sort by the `⁠closest timestamp`, and take the first result. This matches the time skew behavior you learned about earlier - frame content might have been archived at a different time than the parent page.

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

We will use a similar strategy as the download code for the original website snapshots, putting downloaded results into a cache folder. The code is quite verbose, so here is the essential workflow:

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

Run the script with `python 4-download-frames.py` and the `data` folder now includes the downloaded frame files:

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

## Detecting image assets in HTML img tags

Now we have both the original website snapshots and the nested frames. We can start looking for image assets in the `⁠<img>` tags in all the HTML files.

### Retrieving the original website and frame entries

We will use a similar retrieve function to read both the original website and frame entries with adequate metadata:

```python
# util.py (part 9 - api spec)
def retrieve_saved_website_and_frame_entries() -> list[dict]:
    """Retrieve all the saved frame tags for a given website directory
    Returns a list of dicts with the following keys:
    - website_dir: the directory of the website
    - website: the website name
    - cdx_entry: the CDX entry of the website
    - type: "website" or "frame"
    """
```

### Using BeautifulSoup to parse the HTML and find img tags

We will use the same strategy as we did for frame detection, but this time we will look for the `⁠<img>` tags. We will also look for the link in the wrapping `⁠<a>` tags for the `⁠<img>` tags, because most banner ads are wrapped in `⁠<a>` tags to go to the `href` link when clicked. We will save them as `parent_href` and `full_parent_href` (with the full base url) in the `image_tags.json` file.

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

### Detecting all the images in the website and frames

We will run the detect function for every website and frame entry:

```python
# 5-detect-image-tags.py
all_website_and_frame_entries = util.retrieve_saved_website_and_frame_entries()

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

Run the script with `python 5-detect-image-tags.py` and the `data` folder now includes the `image_tags.json` file:

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

As mentioned earlier, in the late 1990s and early 2000s, web developers usually put dimensions in `<img>` tags to help the browser render the layout of the web page before the image loads. We can take advantage of the dimensions provided in the <img> tags to detect banner ads. 

There is a function in `⁠util.py` to check if image dimensions match banner ad criteria:

```python
# util.py (part 11 - api spec)
def check_banner_properties(width: int, height: int) -> dict:
    """Return the banner ad type if the width and height matches the banner ad criteria
    Returns a dict with the following keys:
    - iab_size: the IAB banner category (if fits)
    - jiaa_size: the JIAA banner category (if fits)
    - is_banner_ad: True if the width and height matches the banner ad criteria (either IAB or JIAA)
    """
```

### Retrieving the image tags with parent info

We will use the same strategy as the downloading frames, retrieving all image tags along with their parent website information.

```python
# util.py (part 12 - api spec)
def retrieve_saved_image_tags_with_parent_info() -> list[dict]:
    """Retrieve all the saved image tags for a given website directory
    Returns a list of dicts with the following keys:
    - website_dir: the directory of the website
    - website: the website name
    - cdx_entry: the CDX entry of the website
    - image_tag: the image tag
    """
```

### Downloading banner ad images

We will go through all the image tags with parent info. You will only download the image, if the `width` and `height` recorded in its original `<img>` tag attributes matches any of the IAB or JIAA banner ad dimensions.

Note that the dimension recorded in the `<img>` tag attributes is specified in the HTML file, and is not necessarily represent the actual image file. The discrepancy is amplified even more given the Wayback Machine's time skew, which you will discover in the final summary.

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

Run the script with `python 6-download-banner-ads.py` and the `data` folder now includes the downloaded banner ad files:

```bash
data/
├── example.com/
│   └── 20000510123456/
│       ├── ...
│       ├── banners
│       │   ├── ...
│       │   ├── banners_url_1/
│       │   │   ├── ...
│       │   │   ├── [IMAGE_DIGEST].[ext] # the downloaded image file
│       │   │   ├── image_tag_attrs.json # image tag attributes
│       │   │   ├── cdx_entry.json # cdx entry of the image
```

This process would take several hours depending on your network.

## Summarizing the banner ad collection

You'll now create a comprehensive summary that combines the downloaded banner ad images with their metadata, HTML tag attributes, and archival information. This analysis will reveal interesting discrepancies between what the HTML tags claimed about image dimensions and what the actual image files contain.

### Read image metadata using PIL

You'll use the `PIL` library to read actual image file metadata. The function is defined in `util.py` and here's its specification:

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

### Aggregating various metadata

Along the way, you have gathered metadata from various sources about the image's parent website, `<img>` tag, and the image file itself. The final summary includes comprehensive metadata combining multiple data sources:

- Parent website info
  - `website`
  - `website_timestamp`
- Image CDX entry
  - `urlkey`
  - `timestamp`
  - `original`
  - `mimetype`
  - `statuscode`
  - `digest`
  - `length`
- Image metadata
  - `width`
  - `height`
  - `size`
  - `animated`
  - `frame_count`
  - `animation_duration`
  - `loop_count`
  - `iab_size`
  - `jiaa_size`
  - `corrupt`
- Image tag parameters
  - `image_tag_width`
  - `image_tag_height`
  - `image_tag_banner_iab_size`
  - `image_tag_banner_jiaa_size`
  - `image_tag_parent_href`
  - `image_tag_full_parent_href`
  - `image_tag_alt_text`
- Time skew
  - `time_skew`: the timestamp difference between the image and the parent website in seconds

Run the summary script with `python 7-summarize-banner-ads.py` and the output is `banner-ads-summary.csv`. Here's an example row:

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


DETECTED 12 OUT OF 16 SITES
DOWNLOADED 27 UNIQUE BANNER AD IMAGES
 - SUCCESSFUL 24 UNIQUE BANNERS
   - OF WHICH 8 UNIQUE BANNERS JIA-ONLY
   - THREE IE BUTTONS, TWO VISUALLY IDENTICAL, DIFFERENT FILES, ONE ON BIGLOBE, ONE NIFTY
 - OF UNSUCCESSFULLLY CAPTURED BANNERS
   - 2 TIME SKEW, REDIRECTED TO HTML, 
   - 1 1PXx1PX
 - TIME SKEW FOR 24 UNIQUE BANNERS: 
   - mean, median, mode? 

3 SITES FEATURING JP-ONLY-SIZE BANNER ADS: yahoo, excite, infoseek

LIMITATIONS
90X30 BANNER AD IMAGE - DISCOVERY VIA DOWNLOAD



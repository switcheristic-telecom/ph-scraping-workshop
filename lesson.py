import os
import csv
import json
import requests
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from tenacity import retry, stop_after_attempt, wait_exponential
import time

#############################################
##### STEP 1: UTILITY FUNCTIONS & CLASSES #####
#############################################


CDX_BASE_URL = "https://web.archive.org/cdx/search/cdx"


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


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=2, max=8))
def query_wm_cdx_entries(
    url: str,
    from_time: str = "20000501000000",
    to_time: str = "20000531235959",
):
    """Query the Wayback Machine CDX API for a given URL and time range"""
    cdx_url = f"{CDX_BASE_URL}?url={url}&from={from_time}&to={to_time}"

    response = requests.get(cdx_url, timeout=30)
    response.raise_for_status()

    return parse_wm_cdx_api_response_str(response.text)


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=2, max=8))
def query_wm_cdx_closest_entry(url: str, timestamp: str) -> dict | None:
    """Get the closest snapshot entry for a given URL and timestamp"""
    cdx_url = f"{CDX_BASE_URL}?&limit=1&sort=closest&url={url}&closest={timestamp}"

    response = requests.get(cdx_url, timeout=30)
    response.raise_for_status()

    entries = parse_wm_cdx_api_response_str(response.text)
    return entries[0] if entries else None


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=2, max=8))
def download_snapshot(cdx_entry: dict) -> dict:
    """Download the snapshot file from the Wayback Machine"""
    wayback_url = f"https://web.archive.org/web/{cdx_entry['timestamp']}id_/{cdx_entry['original']}"

    response = requests.get(wayback_url, timeout=30)
    response.encoding = response.apparent_encoding
    response.raise_for_status()
    return {
        "digest": cdx_entry["digest"],
        "mimetype": cdx_entry["mimetype"],
        "statuscode": cdx_entry["statuscode"],
        "length": cdx_entry["length"],
        "file": response.content,
        "encoding": response.encoding,
    }


def ensure_directory(path: str):
    """Create directory if it doesn't exist"""
    os.makedirs(path, exist_ok=True)


#############################################
##### STEP 1: READ JAPANESE WEBSITES #####
#############################################

print("=== STEP 1: Reading Japanese websites from CSV ===")

# Create main output directory
OUTPUT_DIR = "wm_scraping"
ensure_directory(OUTPUT_DIR)
print(f"Created output directory: {OUTPUT_DIR}")

categories_of_interest = ["portal", "content"]

japanese_websites = []
with open("nikkeibp-may2000.csv", "r") as file:
    reader = csv.DictReader(file)
    for row in reader:
        if (
            row.get("is_japanese") == "true"
            and row.get("category") in categories_of_interest
        ):
            japanese_websites.append(row["website"])

print(f"Found {len(japanese_websites)} Japanese websites to scrape")


#############################################
##### STEP 2: QUERY CDX API FOR WEBSITES #####
#############################################

print("\n=== STEP 2: Querying CDX API for website snapshots ===")

for website in japanese_websites:
    print(f"Querying CDX for {website}")
    # Check if website folder already exists (for resumability)
    website_dir = os.path.join(OUTPUT_DIR, website)
    if os.path.exists(website_dir):
        print(f"  Skipping - folder already exists")
        continue

    cdx_entries = query_wm_cdx_entries(website)

    print(f"  Found {len(cdx_entries)} CDX entries")
    ensure_directory(website_dir)

    # Create folder structure for all entries of this website
    if cdx_entries:
        for cdx_entry in cdx_entries:
            website_timestamp_dir = os.path.join(website_dir, cdx_entry["timestamp"])
            ensure_directory(website_timestamp_dir)

            cdx_meta_path = os.path.join(website_timestamp_dir, "cdx_entry.json")
            with open(cdx_meta_path, "w") as f:
                json.dump(cdx_entry, f, indent=2)

        print(f"  Created {len(cdx_entries)} snapshot entry folders")

    time.sleep(1)  # Be respectful to the API


#############################################
##### STEP 3: DOWNLOAD WEBSITE SNAPSHOTS #####
#############################################

print("\n=== STEP 3: Downloading website snapshots ===")

all_website_entries = {}

for website in japanese_websites:
    website_dir = os.path.join(OUTPUT_DIR, website)
    all_website_entries[website] = []
    for timestamp_dir in os.listdir(website_dir):
        if os.path.isdir(os.path.join(website_dir, timestamp_dir)):
            cdx_meta_path = os.path.join(website_dir, timestamp_dir, "cdx_entry.json")
            with open(cdx_meta_path, "r") as f:
                cdx_entry = json.load(f)
            all_website_entries[website].append(cdx_entry)

# Calculate total number of snapshots across all websites
total_snapshots = sum(len(entries) for entries in all_website_entries.values())
print(
    f"Found {len(all_website_entries)} websites with {total_snapshots} total snapshots"
)


def save_website_snapshot(website: str, cdx_entry: dict, snapshot: dict):
    """Save a website snapshot with the folder structure"""
    # Create website directory
    website_dir = os.path.join(OUTPUT_DIR, website, cdx_entry["timestamp"])
    ensure_directory(website_dir)

    # Save main HTML file (original encoding)
    html_filename = f"{cdx_entry['digest']}.html"
    html_path = os.path.join(website_dir, html_filename)
    with open(html_path, "wb") as f:
        f.write(snapshot["file"])

    # Save decoded UTF-8 version of HTML
    decoded_content = snapshot["file"].decode(snapshot["encoding"], errors="replace")
    utf8_html_filename = f"{cdx_entry['digest']}_utf8.html"
    utf8_html_path = os.path.join(website_dir, utf8_html_filename)
    with open(utf8_html_path, "w", encoding="utf-8") as f:
        f.write(decoded_content)

    # Save encoding information
    encoding_path = os.path.join(website_dir, "encoding.txt")
    with open(encoding_path, "w") as f:
        f.write(snapshot["encoding"])

    return website_dir, html_path


for website, entries in all_website_entries.items():
    print(f"Found {len(entries)} snapshots for {website}")

    # Download ALL entries for each website
    for cdx_entry in entries:
        website_dir = os.path.join(OUTPUT_DIR, website, cdx_entry["timestamp"])

        # Check if snapshot has already been downloaded
        html_filename = f"{cdx_entry['digest']}.html"
        html_path = os.path.join(website_dir, html_filename)

        if os.path.exists(html_path):
            print(f"  Skipping {cdx_entry['timestamp']} - already downloaded")
            continue

        print(f"  Downloading snapshot from {cdx_entry['timestamp']}")

        try:
            snapshot = download_snapshot(cdx_entry)
            website_dir, html_path = save_website_snapshot(website, cdx_entry, snapshot)
            print(f"    Saved snapshot to {website_dir}")
            time.sleep(1)  # Be respectful to the API
        except Exception as e:
            print(f"    Error downloading {cdx_entry['timestamp']}: {e}")
            continue

#############################################
##### STEP 4: EXTRACT CHILD RESOURCES #####
#############################################

exit()

print("\n=== STEP 4: Extracting child resources from HTML ===")


def find_child_resources(soup: BeautifulSoup, base_url: str) -> list[str]:
    """Find all child resource URLs in the BeautifulSoup object"""
    resources = []

    # Find images
    for img in soup.find_all("img"):
        src = img.get("src")
        if src:
            full_url = urljoin(base_url, src)
            resources.append(full_url)

    # Find frame sources (for framesets)
    for frame in soup.find_all("frame"):
        src = frame.get("src")
        if src:
            full_url = urljoin(base_url, src)
            resources.append(full_url)

    # Find iframe sources
    for iframe in soup.find_all("iframe"):
        src = iframe.get("src")
        if src:
            full_url = urljoin(base_url, src)
            resources.append(full_url)

    return resources


def is_frameset_html(content: str) -> bool:
    """Check if HTML content contains framesets"""
    return "<frameset" in content.lower() or "<frame " in content.lower()


def process_child_resources(
    website_dir: str, html_path: str, original_url: str, reference_timestamp: str
):
    """Process and download child resources for a website"""
    # Read and parse the HTML
    with open(html_path, "rb") as f:
        content = f.read()

    try:
        decoded_content = content.decode("utf-8", errors="ignore")
    except:
        try:
            decoded_content = content.decode("iso-8859-1", errors="ignore")
        except:
            print(f"Could not decode HTML content for {html_path}")
            return

    soup = BeautifulSoup(decoded_content, "html.parser")

    # Find child resources
    child_urls = find_child_resources(soup, original_url)

    if not child_urls:
        print(f"No child resources found for {original_url}")
        return

    print(f"Found {len(child_urls)} child resources for {original_url}")

    # Save children asset map
    children_assets_path = os.path.join(website_dir, "children_assets.json")
    with open(children_assets_path, "w") as f:
        json.dump(child_urls, f, indent=2)

    # Create assets directory
    assets_dir = os.path.join(website_dir, "assets")
    ensure_directory(assets_dir)

    # Download each child resource
    for child_url in child_urls:
        try:
            print(f"  Querying CDX for {child_url}")
            child_cdx_entry = query_wm_cdx_closest_entry(child_url, reference_timestamp)

            if not child_cdx_entry:
                print(f"  No CDX entry found for {child_url}")
                continue

            print(f"  Downloading {child_url}")
            child_snapshot = download_snapshot(child_cdx_entry)

            # Determine file extension based on mimetype
            file_ext = get_file_extension(child_cdx_entry.mimetype, child_url)
            child_filename = f"{child_cdx_entry.digest}{file_ext}"
            child_path = os.path.join(assets_dir, child_filename)

            # Save child resource file
            with open(child_path, "wb") as f:
                f.write(child_snapshot.file)

            # Calculate time drift in seconds (simple string comparison)
            # Convert timestamps to integers for simple subtraction
            try:
                child_ts = int(child_cdx_entry.timestamp)
                ref_ts = int(reference_timestamp)
                time_drift_seconds = abs(child_ts - ref_ts)
            except:
                time_drift_seconds = 0  # Fallback if conversion fails

            # Save child CDX metadata
            child_cdx_meta = {
                "urlkey": child_cdx_entry.urlkey,
                "timestamp": child_cdx_entry.timestamp,
                "original": child_cdx_entry.original,
                "mimetype": child_cdx_entry.mimetype,
                "statuscode": child_cdx_entry.statuscode,
                "digest": child_cdx_entry.digest,
                "length": child_cdx_entry.length,
                "encoding": child_snapshot.encoding,
                "time_drift_seconds": time_drift_seconds,
            }

            child_meta_path = os.path.join(
                assets_dir, f"{child_cdx_entry.digest}_cdx_entry.json"
            )
            with open(child_meta_path, "w") as f:
                json.dump(child_cdx_meta, f, indent=2)

            # If it's a frameset HTML, recursively process it
            if child_cdx_entry.mimetype == "text/html" and is_frameset_html(
                child_snapshot.file.decode(child_snapshot.encoding, errors="ignore")
            ):
                print(f"  Processing frameset: {child_url}")
                frame_dir = os.path.join(assets_dir, f"{child_cdx_entry.digest}_frame")
                ensure_directory(frame_dir)

                # Save frameset HTML in its own directory
                frame_html_path = os.path.join(
                    frame_dir, f"{child_cdx_entry.digest}.html"
                )
                with open(frame_html_path, "wb") as f:
                    f.write(child_snapshot.file)

                # Recursively process the frameset
                process_child_resources(
                    frame_dir, frame_html_path, child_url, child_cdx_entry.timestamp
                )

            time.sleep(0.5)  # Be respectful to the API

        except Exception as e:
            print(f"  Error processing {child_url}: {e}")


def get_file_extension(mimetype: str, url: str) -> str:
    """Get appropriate file extension based on mimetype and URL"""
    # Extract extension from URL first
    parsed_url = urlparse(url)
    path = parsed_url.path
    if "." in path:
        return "." + path.split(".")[-1].lower()

    # Fallback to mimetype mapping
    mimetype_mapping = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/bmp": ".bmp",
        "text/html": ".html",
        "text/css": ".css",
        "application/javascript": ".js",
        "text/javascript": ".js",
        "audio/midi": ".mid",
        "audio/mpeg": ".mp3",
        "video/mpeg": ".mpg",
        "application/octet-stream": ".bin",
    }

    return mimetype_mapping.get(mimetype, ".bin")


# Process child resources for each downloaded website
for website, cdx_entry, website_dir, html_path in downloaded_websites:
    # Check if child resources have already been processed
    children_assets_path = os.path.join(website_dir, "children_assets.json")
    if os.path.exists(children_assets_path):
        print(f"Skipping child resource processing for {website} - already processed")
        continue

    print(f"\nProcessing child resources for {website}")
    process_child_resources(
        website_dir, html_path, cdx_entry.original, cdx_entry.timestamp
    )

#############################################
##### STEP 6: SUMMARY #####
#############################################

print("\n=== STEP 6: Summary ===")
print(f"Processed {len(japanese_websites)} Japanese websites")
print(f"Successfully downloaded {len(downloaded_websites)} website snapshots")
print("\nFolder structure created:")
print("wm_scraping/")
print("  website_domain/")
print("    timestamp1/")
print("      digest.html (main HTML file)")
print("      cdx_entry.json (CDX metadata)")
print("      children_assets.json (list of child URLs)")
print("      assets/")
print("        asset_digest.ext (downloaded assets)")
print("        asset_digest_cdx_entry.json (asset CDX metadata)")
print("        frameset_digest_frame/ (recursive framesets)")
print("          ...")
print("    timestamp2/")
print("      ...")
print("    timestamp3/")
print("      ...")

print("\nScraping complete! Check the created directories for downloaded content.")
print("\nNOTE: This script is resumable - if interrupted, you can run it again")
print("and it will skip websites that have already been processed completely.")

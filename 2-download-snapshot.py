import os, csv, json, time, requests
from tenacity import retry, stop_after_attempt, wait_exponential

#####################
##### CONSTANTS #####
#####################

OUTPUT_DIR = "wm_scraping"
os.makedirs(OUTPUT_DIR, exist_ok=True)

all_website_entries = {}

for website in os.listdir(OUTPUT_DIR):
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


@retry(stop=stop_after_attempt(10), wait=wait_exponential(multiplier=1, min=2, max=8))
def download_snapshot(cdx_entry: dict) -> dict:
    wayback_url = f"https://web.archive.org/web/{cdx_entry['timestamp']}id_/{cdx_entry['original']}"

    response = requests.get(wayback_url, timeout=30)
    response.encoding = response.apparent_encoding
    response.raise_for_status()
    return {
        "file": response.content,
        "encoding": response.encoding,
    }


def save_website_snapshot(website: str, cdx_entry: dict, snapshot: dict):
    """Save a website snapshot with the folder structure"""
    # Create website directory
    website_dir = os.path.join(OUTPUT_DIR, website, cdx_entry["timestamp"])
    os.makedirs(website_dir, exist_ok=True)

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

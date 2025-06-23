import os, json
import util
from bs4 import BeautifulSoup

OUTPUT_DIR = "data"
CACHE_DIR = "cache"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

all_website_entries = util.get_saved_website_entries()


for entry in all_website_entries:
    website = entry["website"]
    snapshot_dir = entry["snapshot_dir"]
    cdx_entry = entry["cdx_entry"]

    print(f"{entry['website']} at {cdx_entry['timestamp']}")

    # Check if snapshot has already been downloaded
    utf8_html_filename = f"{cdx_entry['digest']}_utf8.html"
    utf8_html_path = os.path.join(snapshot_dir, utf8_html_filename)

    if not os.path.exists(utf8_html_path):
        print(f"  Skipping {cdx_entry['timestamp']} - not downloaded")
        continue

    with open(utf8_html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
        util.detect_and_save_frame_tag_attrs(soup, snapshot_dir)
        print(f"  Found {len(soup.find_all('frame'))} frame tags")

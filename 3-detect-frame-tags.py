import os, json
import util


all_website_entries = util.get_saved_website_entries()


from bs4 import BeautifulSoup

OUTPUT_DIR = "data"
CACHE_DIGEST_DIR = "cache-digest"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_DIGEST_DIR, exist_ok=True)

for website, entries in all_website_entries.items():
    print(f"Found {len(entries)} snapshots for {website}")

    # Detect all frame tags in each snapshot
    for cdx_entry in entries:
        print(f"    Timestamp: {cdx_entry['timestamp']}")
        website_dir = os.path.join(OUTPUT_DIR, website, cdx_entry["timestamp"])

        # Check if snapshot has already been downloaded
        utf8_html_filename = f"{cdx_entry['digest']}_utf8.html"
        utf8_html_path = os.path.join(website_dir, utf8_html_filename)

        if not os.path.exists(utf8_html_path):
            print(f"      Skipping {cdx_entry['timestamp']} - not downloaded")
            continue

        with open(utf8_html_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
            util.detect_and_save_frame_tag_attrs(soup, website_dir)
            print(f"      Found {len(soup.find_all('frame'))} frame tags")

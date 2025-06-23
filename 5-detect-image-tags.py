import os, json
import util

##################
##### PART 1 #####
##################
from bs4 import BeautifulSoup

OUTPUT_DIR = "data"
CACHE_DIR = "cache"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

all_website_and_frame_entries = util.retrieve_saved_website_and_frame_entries()

print(f"Found {len(all_website_and_frame_entries)} website and frame entries")

# Detect all images in the website and frame entries
for entry in all_website_and_frame_entries:
    website = entry["website"]
    website_dir = entry["website_dir"]
    cdx_entry = entry["cdx_entry"]
    print(f"{entry['type']} Entry at {website_dir}")

    # Check if snapshot has already been downloaded
    utf8_html_filename = f"{cdx_entry['digest']}_utf8.html"
    utf8_html_path = os.path.join(website_dir, utf8_html_filename)

    if not os.path.exists(utf8_html_path):
        print(f"      Skipping {cdx_entry['timestamp']} - not downloaded")
        continue

    with open(utf8_html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
        image_tags = util.detect_and_save_image_tag_attrs(soup, website_dir, cdx_entry)
        print(f"      Found {len(image_tags)} image tags")

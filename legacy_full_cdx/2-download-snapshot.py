import os, json
import util

#####################
##### CONSTANTS #####
#####################

OUTPUT_DIR = "data"
CACHE_DIR = "cache"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

################
##### MAIN #####
################

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
            continue

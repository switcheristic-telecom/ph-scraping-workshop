import os, json
import util

##################
##### PART 1 #####
##################

all_website_entries = util.get_saved_website_entries()

##################
##### PART 2 #####
##################

OUTPUT_DIR = "data"
CACHE_DIGEST_DIR = "cache-digest"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_DIGEST_DIR, exist_ok=True)


for entry in all_website_entries:
    snapshot_dir = entry["snapshot_dir"]
    cdx_entry = entry["cdx_entry"]

    # Check if snapshot has already been downloaded
    html_filename = f"{cdx_entry['digest']}.html"
    html_path = os.path.join(snapshot_dir, html_filename)

    if os.path.exists(html_path):
        print(f"  Skipping {cdx_entry['timestamp']} - already downloaded")
        continue

    # Check if snapshot has already been cached
    cache_snapshot_dir = os.path.join(CACHE_DIGEST_DIR, cdx_entry["digest"])
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

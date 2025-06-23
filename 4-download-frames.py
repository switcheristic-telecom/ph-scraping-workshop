import os, json
import util

##################
##### PART 1 #####
##################
import urllib.parse

OUTPUT_DIR = "data"
CACHE_DIGEST_DIR = "cache-digest"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_DIGEST_DIR, exist_ok=True)

all_frame_tags_with_parent_info = util.get_saved_frame_tags_with_parent_info()

print(f"Found {len(all_frame_tags_with_parent_info)} frame tags")

for frame_tag_with_parent_info in all_frame_tags_with_parent_info:
    frame_tag = frame_tag_with_parent_info["frame_tags"]
    website = frame_tag_with_parent_info["website"]
    website_dir = frame_tag_with_parent_info["website_dir"]
    cdx_entry = frame_tag_with_parent_info["parent_cdx_entry"]

    print(f"Parent: {website} at {cdx_entry['timestamp']}")
    frame_tag_src = frame_tag["src"]
    print(f"    Frame src: {frame_tag_src}")

    # If frame tag src is a full URL, use it as is, else join with original URL
    if frame_tag_src.startswith("http"):
        actual_frame_url = frame_tag_src
    else:
        actual_frame_url = urllib.parse.urljoin(cdx_entry["original"], frame_tag_src)

    frame_snapshot_dir = os.path.join(
        website_dir, "frames", util.url_to_filename(frame_tag_src)
    )
    os.makedirs(frame_snapshot_dir, exist_ok=True)

    # Check if CDX entry already exists, if not, query CDX
    frame_cdx_entry_path = os.path.join(frame_snapshot_dir, "cdx_entry.json")
    if os.path.exists(frame_cdx_entry_path):
        with open(frame_cdx_entry_path, "r") as f:
            frame_cdx_entry = json.load(f)
        print(f"        Found CDX entry for {frame_tag_src}")
    else:
        print(
            f"        Querying CDX for {actual_frame_url} at {cdx_entry['timestamp']}"
        )
        frame_cdx_entry = util.query_wm_cdx_closest_entry(
            actual_frame_url, cdx_entry["timestamp"]
        )
        with open(frame_cdx_entry_path, "w") as f1:
            json.dump(frame_cdx_entry, f1)

    # If CDX entry is valid, download snapshot
    if frame_cdx_entry:
        frame_snapshot_file_path = os.path.join(
            frame_snapshot_dir, f"{frame_cdx_entry['digest']}.html"
        )
        # Check if snapshot already exists, if not, download snapshot
        if os.path.exists(frame_snapshot_file_path):
            print(f"        Skipping {frame_tag_src} - already downloaded")
            continue

        cache_frame_snapshot_dir = os.path.join(
            CACHE_DIGEST_DIR, frame_cdx_entry["digest"]
        )
        try:
            print(f"        Downloading frame {frame_tag_src}")
            frame_snapshot = util.download_website_snapshot(frame_cdx_entry)
            util.save_website_snapshot(frame_snapshot, frame_snapshot_dir)
            util.save_website_snapshot(frame_snapshot, cache_frame_snapshot_dir)

            print(f"        Saved frame to {frame_snapshot_dir}")
        except Exception as e:
            print(
                f"    Error downloading {frame_tag_src} at {cdx_entry['timestamp']}: {e}"
            )

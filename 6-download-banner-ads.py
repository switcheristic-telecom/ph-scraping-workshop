import os, json
import util
import urllib.parse

CACHE_DIR = "cache"

all_image_tags_with_parent_info = util.get_saved_image_tags_with_parent_info()

print(f"Found {len(all_image_tags_with_parent_info)} image tags")

for image_tag_with_parent_info in all_image_tags_with_parent_info:
    image_tag = image_tag_with_parent_info["image_tag"]
    website = image_tag_with_parent_info["website"]
    website_dir = image_tag_with_parent_info["website_dir"]
    cdx_entry = image_tag_with_parent_info["cdx_entry"]

    # Skip if it's missing src, width, or height
    if "src" not in image_tag or "width" not in image_tag or "height" not in image_tag:
        print(f"Skipping {website} because it doesn't have src, width, or height")
        continue

    image_tag_src = image_tag["src"]
    width = int(image_tag["width"])
    height = int(image_tag["height"])
    # If image tag src is a full URL, use it as is, else join with original URL
    if image_tag_src.startswith("http"):
        actual_image_url = image_tag_src
    else:
        actual_image_url = urllib.parse.urljoin(cdx_entry["original"], image_tag_src)

    banner_properties = util.check_banner_properties(width, height)

    if not banner_properties["is_banner_ad"]:
        print(
            f"Skipping {actual_image_url} because it's not a banner ad: {width}x{height}"
        )
        continue

    print(f"Banner ad found: {actual_image_url} {width}x{height}")

    banner_snapshot_dir = os.path.join(
        website_dir, "banners", util.url_to_filename(image_tag_src)
    )
    os.makedirs(banner_snapshot_dir, exist_ok=True)

    # Check if CDX entry already exists, if not, query CDX
    banner_cdx_entry_path = os.path.join(banner_snapshot_dir, "cdx_entry.json")
    if os.path.exists(banner_cdx_entry_path):
        with open(banner_cdx_entry_path, "r") as f:
            banner_cdx_entry = json.load(f)
        print(f"        Found CDX entry for {image_tag_src}")
    else:
        print(
            f"        Querying CDX for {actual_image_url} at {cdx_entry['timestamp']}"
        )
        banner_cdx_entry = util.query_wm_cdx_closest_entry(
            actual_image_url, cdx_entry["timestamp"]
        )
        with open(banner_cdx_entry_path, "w") as f1:
            json.dump(banner_cdx_entry, f1)

    # If CDX entry is valid, download snapshot
    if banner_cdx_entry and banner_cdx_entry["statuscode"] == "200":
        extension = util.get_image_file_extension(banner_cdx_entry)
        banner_snapshot_file_path = os.path.join(
            banner_snapshot_dir, f"{banner_cdx_entry['digest']}.{extension}"
        )
        banner_image_tag_file_path = os.path.join(
            banner_snapshot_dir, "image_tag_attrs.json"
        )
        with open(banner_image_tag_file_path, "w") as f:
            json.dump(image_tag_with_parent_info["image_tag"], f)

        # Check if snapshot already exists, if not, proceed
        if os.path.exists(banner_snapshot_file_path):
            print(f"        Skipping {image_tag_src} - already downloaded")
            continue

        cache_banner_snapshot_dir = os.path.join(CACHE_DIR, banner_cdx_entry["digest"])
        # Check if snapshot already exists in cache, if not, proceed
        if util.find_and_copy_cached_snapshot(
            cache_banner_snapshot_dir, banner_snapshot_dir
        ):
            print(f"        Skipping {image_tag_src} - found in cache")

            continue

        try:
            print(f"        Downloading banner {image_tag_src}")
            banner_snapshot = util.download_image_snapshot(banner_cdx_entry)
            util.save_image_snapshot(banner_snapshot, banner_snapshot_dir)
            util.save_image_snapshot(banner_snapshot, cache_banner_snapshot_dir)

            print(f"        Saved banner to {banner_snapshot_dir}")
        except Exception as e:
            print(
                f"    Error downloading {image_tag_src} at {cdx_entry['timestamp']}: {e}"
            )

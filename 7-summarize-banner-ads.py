import os, json, csv
import util

OUTPUT_DIR = "data"
CACHE_DIR = "cache"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)


def detect_images(snapshot_dir: str):
    """Walk through website directory and find all image files using util.image_extensions"""
    images = []

    # Walk through all subdirectories
    for root, dirs, files in os.walk(snapshot_dir):
        for filename in files:
            # Check if file has an image extension
            if filename.endswith(tuple(util.image_extensions)):
                file_path = os.path.join(root, filename)

                # Look for associated metadata files in the same directory
                cdx_entry_path = os.path.join(root, "cdx_entry.json")
                image_tag_attrs_path = os.path.join(root, "image_tag_attrs.json")

                # Get image metadata using util function
                metadata = util.get_image_metadata(file_path)

                # Load CDX entry and image tag attributes
                with open(cdx_entry_path, "r") as f:
                    cdx_entry = json.load(f)

                with open(image_tag_attrs_path, "r") as f:
                    image_tag_attrs = json.load(f)

                images.append(
                    {
                        "path": file_path,
                        "metadata": metadata,
                        "cdx_entry": cdx_entry,
                        "image_tag_attrs": image_tag_attrs,
                    }
                )

    return images


all_images = []

for website in os.listdir(OUTPUT_DIR):
    website_dir = os.path.join(OUTPUT_DIR, website)
    for timestamp in os.listdir(website_dir):
        snapshot_dir = os.path.join(website_dir, timestamp)
        print(snapshot_dir)
        if os.path.isdir(snapshot_dir):
            for image in detect_images(snapshot_dir):

                image_tag_height = image["image_tag_attrs"].get("height", None)
                image_tag_width = image["image_tag_attrs"].get("width", None)
                if image_tag_height and image_tag_width:
                    image_tag_banner_properties = util.check_banner_properties(
                        int(image_tag_width), int(image_tag_height)
                    )

                all_images.append(
                    {
                        "website": website,
                        "website_timestamp": timestamp,
                        **image["cdx_entry"],
                        **image["metadata"],
                        "image_tag_width": image_tag_width,
                        "image_tag_height": image_tag_height,
                        "image_tag_banner_iab_size": image_tag_banner_properties.get(
                            "iab_size", None
                        ),
                        "image_tag_banner_jiaa_size": image_tag_banner_properties.get(
                            "jiaa_size", None
                        ),
                        "image_tag_parent_href": image["image_tag_attrs"].get(
                            "parent_href", None
                        ),
                        "image_tag_full_parent_href": image["image_tag_attrs"].get(
                            "full_parent_href", None
                        ),
                        "image_tag_alt_text": image["image_tag_attrs"].get("alt", None),
                    }
                )


with open("banner-ads-summary.csv", "w", newline="", encoding="utf-8") as f:
    fieldnames = ["website", "website_timestamp"] + [
        k for k in all_images[0].keys() if k not in ["website", "website_timestamp"]
    ]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(all_images)

print(f"Found {len(all_images)} images")

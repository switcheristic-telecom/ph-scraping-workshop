import os, json, csv
import util

OUTPUT_DIR = "data"
CACHE_DIR = "cache"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

image_extensions = [
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".webp",
    ".bmp",
    ".ico",
    ".tiff",
    ".tif",
]


def detect_images(website_dir: str):
    images = []
    for root, dirs, files in os.walk(website_dir):
        for resource_name in files:
            if resource_name.endswith(tuple(image_extensions)):
                file_path = os.path.join(root, resource_name)
                cdx_entry_path = os.path.join(root, "cdx_entry.json")
                image_tag_attrs_path = os.path.join(root, "image_tag_attrs.json")
                metadata = util.get_image_metadata(file_path)
                images.append(
                    {
                        "path": file_path,
                        "metadata": metadata,
                        "cdx_entry": json.load(open(cdx_entry_path)),
                        "image_tag_attrs": json.load(open(image_tag_attrs_path)),
                    }
                )

    return images


all_images = []

for website in os.listdir(OUTPUT_DIR):
    website_dir = os.path.join(OUTPUT_DIR, website)
    for timestamp in os.listdir(website_dir):
        snapshot_dir = os.path.join(website_dir, timestamp)
        if os.path.isdir(snapshot_dir):
            for image in detect_images(snapshot_dir):
                all_images.append(
                    {
                        "website": website,
                        "website_timestamp": timestamp,
                        **image["cdx_entry"],
                        **image["metadata"],
                        "image_tag_parent_href": image["image_tag_attrs"].get(
                            "parent_href", None
                        ),
                        "image_tag_full_parent_href": image["image_tag_attrs"].get(
                            "full_parent_href", None
                        ),
                        "image_tag_alt_text": image["image_tag_attrs"].get("alt", None),
                    }
                )

with open("image-summary.csv", "w", newline="", encoding="utf-8") as f:
    fieldnames = ["website", "website_timestamp"] + [
        k for k in all_images[0].keys() if k not in ["website", "website_timestamp"]
    ]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(all_images)

print(f"Found {len(all_images)} images")

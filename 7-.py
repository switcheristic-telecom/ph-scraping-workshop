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


def get_image_metadata(image_path: str):
    from PIL import Image

    with Image.open(image_path) as img:
        metadata = {
            "width": img.width,
            "height": img.height,
            "size": os.path.getsize(image_path),
            "animated": False,
            "frame_count": 1,
            "animation_duration": 0,
            "loop_count": 0,
            "iab_size": None,
            "jiaa_size": None,
        }

        # Check for GIF animation
        if img.format == "GIF" and "duration" in img.info:
            try:
                metadata["animated"] = True
                metadata["frame_count"] = img.n_frames
                metadata["animation_duration"] = (
                    img.info.get("duration", 0) * img.n_frames
                )
                metadata["loop_count"] = img.info.get("loop", 0)
            except (AttributeError, KeyError):
                pass

        banner_metadata = util.check_banner_properties(
            metadata["width"], metadata["height"]
        )

        metadata["iab_size"] = banner_metadata["iab_size"]
        metadata["jiaa_size"] = banner_metadata["jiaa_size"]

        return metadata


def detect_images(snapshot_dir: str):
    resources_dir = os.path.join(snapshot_dir, "resources")
    images = []
    for root, dirs, files in os.walk(resources_dir):
        for resource_name in files:
            if resource_name.endswith(tuple(image_extensions)):
                file_path = os.path.join(root, resource_name)
                cdx_entry_path = os.path.join(root, "cdx_entry.json")
                image_tag_attrs_path = os.path.join(root, "image_tag_attrs.json")
                metadata = get_image_metadata(file_path)
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

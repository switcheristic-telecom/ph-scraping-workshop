import os, json, urllib.parse
from bs4 import BeautifulSoup
import util


OUTPUT_DIR = "data"
CACHE_DIR = "cache"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)


def capture_website_resources(website_dir: str, cdx_entry: dict):
    utf8_html_filename = f"{cdx_entry['digest']}_utf8.html"
    utf8_html_path = os.path.join(website_dir, utf8_html_filename)

    with open(utf8_html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
        resources_dir = os.path.join(website_dir, "resources")
        os.makedirs(resources_dir, exist_ok=True)
        capture_images(resources_dir, cdx_entry, soup)
        capture_frames(resources_dir, cdx_entry, soup)


def capture_images(resources_dir: str, cdx_entry: dict, soup: BeautifulSoup):
    for img in soup.find_all("img"):
        if img["src"].startswith("http"):
            img_url = img["src"]
        else:
            img_url = urllib.parse.urljoin(cdx_entry["original"], img["src"])

        image_tag_attrs = img.attrs

        if img.parent.name == "a":
            image_tag_attrs["parent_href"] = img.parent["href"]
            if img.parent["href"].startswith("http"):
                image_tag_attrs["full_parent_href"] = img.parent["href"]
            else:
                image_tag_attrs["full_parent_href"] = urllib.parse.urljoin(
                    cdx_entry["original"], img.parent["href"]
                )

        resource_name = util.safe_filename(img["src"])
        resource_cdx_entry_path = os.path.join(resources_dir, resource_name + ".json")

        print(f"  Found image {img_url} ({cdx_entry['timestamp']})")

        if os.path.exists(resource_cdx_entry_path):
            with open(resource_cdx_entry_path, "r") as f:
                closest_entry = json.load(f)
        else:
            closest_entry = util.query_wm_cdx_closest_entry(
                img_url, cdx_entry["timestamp"]
            )
            with open(resource_cdx_entry_path, "w") as f:
                json.dump(closest_entry, f)

        if not closest_entry:
            print(f"    No closest entry found for {img_url}")
            continue

        print(f"    Closest cdx entry: {closest_entry['digest']}")

        image_dir = os.path.join(resources_dir, resource_name)
        cache_image_dir = os.path.join(CACHE_DIR, closest_entry["digest"])

        if closest_entry["statuscode"] == "200":
            if util.find_and_copy_cached_snapshot(cache_image_dir, image_dir):
                print(f"    Loaded from cache {img_url}, skipping")

            else:
                print(f"    Downloading image {img_url} ({closest_entry['digest']})")
                image_snapshot = util.download_image(closest_entry)

                util.save_image(image_snapshot, image_dir)
                util.save_image(image_snapshot, cache_image_dir)

            with open(os.path.join(image_dir, "cdx_entry.json"), "w") as f:
                json.dump(closest_entry, f)

            with open(os.path.join(image_dir, "image_tag_attrs.json"), "w") as f:
                json.dump(image_tag_attrs, f)


def capture_frames(resources_dir: str, cdx_entry: dict, soup: BeautifulSoup):
    for frame in soup.find_all("frame"):
        if frame["src"].startswith("http"):
            frame_url = frame["src"]
        else:
            frame_url = urllib.parse.urljoin(cdx_entry["original"], frame["src"])

        print(f"    Found frame {frame_url} ({cdx_entry['timestamp']})")

        resource_name = util.safe_filename(frame["src"])
        resource_cdx_entry_path = os.path.join(resources_dir, resource_name + ".json")

        if os.path.exists(resource_cdx_entry_path):
            with open(resource_cdx_entry_path, "r") as f:
                closest_entry = json.load(f)
        else:
            closest_entry = util.query_wm_cdx_closest_entry(
                frame_url, cdx_entry["timestamp"]
            )
            with open(resource_cdx_entry_path, "w") as f:
                json.dump(closest_entry, f)

        if not closest_entry:
            print(f"    No closest entry found for {frame_url}")
            continue

        print(f"    Closest cdx entry: {closest_entry['digest']}")

        frame_dir = os.path.join(resources_dir, resource_name)
        cache_frame_dir = os.path.join(CACHE_DIR, closest_entry["digest"])

        if closest_entry["statuscode"] == "200":
            if util.find_and_copy_cached_snapshot(cache_frame_dir, frame_dir):
                print(f"    Loaded from cache {frame_url}, skipping")
            else:
                print(f"    Downloading frame {frame_url} ({closest_entry['digest']})")
                frame_snapshot = util.download_website_snapshot(closest_entry)
                util.save_website_snapshot(frame_snapshot, frame_dir)
                util.save_website_snapshot(frame_snapshot, cache_frame_dir)

        cdx_entry_path = os.path.join(frame_dir, "cdx_entry.json")
        with open(cdx_entry_path, "w") as f:
            json.dump(closest_entry, f)

        capture_website_resources(frame_dir, closest_entry)


################
##### MAIN #####
################


# Load all website cdx entries
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

import random

# Randomize order of websites
websites = list(all_website_entries.items())
random.shuffle(websites)

for website, entries in websites:
    print(f"Found {len(entries)} snapshots for {website}")

    # Randomize order of entries
    shuffled_entries = entries.copy()
    random.shuffle(shuffled_entries)

    # Download ALL entries for each website
    for cdx_entry in shuffled_entries:
        print(f"Found {cdx_entry['timestamp']} {cdx_entry['digest']}")

        website_dir = os.path.join(OUTPUT_DIR, website, cdx_entry["timestamp"])

        # Check if snapshot has already been downloaded
        utf8_html_filename = f"{cdx_entry['digest']}_utf8.html"
        utf8_html_path = os.path.join(website_dir, utf8_html_filename)

        if not os.path.exists(utf8_html_path):
            print(f"  Skipping {cdx_entry['timestamp']} - not downloaded")
            continue

        capture_website_resources(website_dir, cdx_entry)

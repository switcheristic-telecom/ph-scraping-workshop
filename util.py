##################
##### PART 1 #####
##################

import requests, time, tenacity

retry = tenacity.retry(
    stop=tenacity.stop_after_attempt(10),
    wait=tenacity.wait_exponential(multiplier=1, min=2, max=32),
    after=lambda _: time.sleep(2),
)


def parse_wm_cdx_api_response_str(response_str: str) -> list[dict]:
    """Parse the response from the Wayback Machine CDX API"""
    rows = [entry for entry in response_str.strip().split("\n") if entry != ""]
    result = []
    for row in rows:
        fields = row.split(" ")
        result.append(
            {
                "urlkey": fields[0],
                "timestamp": fields[1],
                "original": fields[2],
                "mimetype": fields[3],
                "statuscode": fields[4],
                "digest": fields[5],
                "length": fields[6],
            }
        )
    return result


@retry
def query_wm_cdx_entries(
    url: str,
    from_time: str = "20000501000000",
    to_time: str = "20000531235959",
):
    """Query the Wayback Machine CDX API for a given URL and time range"""
    cdx_url = f"https://web.archive.org/cdx/search/cdx?url={url}&from={from_time}&to={to_time}"

    response = requests.get(cdx_url, timeout=30)
    response.raise_for_status()

    return parse_wm_cdx_api_response_str(response.text)


##################
##### PART 2 #####
##################
import os, json

OUTPUT_DIR = "data"


def retrieve_saved_website_entries() -> list[dict]:
    """Retrieve all the saved website entries
    Returns a list of dicts with the following keys:
    - website: the website name
    - snapshot_dir: the directory of the website snapshot
    - cdx_entry: the CDX entry of the website
    """
    all_website_entries = []

    for website in os.listdir(OUTPUT_DIR):
        website_dir = os.path.join(OUTPUT_DIR, website)

        for timestamp_dir in os.listdir(website_dir):
            if os.path.isdir(os.path.join(website_dir, timestamp_dir)):
                website_snapshot_dir = os.path.join(website_dir, timestamp_dir)
                cdx_meta_path = os.path.join(website_snapshot_dir, "cdx_entry.json")
                with open(cdx_meta_path, "r") as f:
                    cdx_entry = json.load(f)
                all_website_entries.append(
                    {
                        "website": website,
                        "snapshot_dir": website_snapshot_dir,
                        "cdx_entry": cdx_entry,
                    }
                )

    return all_website_entries


##################
##### PART 3 #####
##################


@retry
def download_website_snapshot(cdx_entry: dict) -> dict:
    """Download a website snapshot from the Wayback Machine
    Returns a dict with the following keys:
    - digest: the digest of the website
    - file: the website file
    - encoding: the encoding of the website
    """
    wayback_url = f"https://web.archive.org/web/{cdx_entry['timestamp']}id_/{cdx_entry['original']}"
    response = requests.get(wayback_url, timeout=30)
    response.raise_for_status()
    return {
        "digest": cdx_entry["digest"],
        "file": response.content,
        "encoding": response.apparent_encoding,
    }


def save_website_snapshot(snapshot: dict, save_dir: str):
    """Save a website snapshot (original and utf8 versions) and encoding information to a directory"""
    os.makedirs(save_dir, exist_ok=True)

    # Save main HTML file (original encoding)
    html_filename = f"{snapshot['digest']}.html"
    with open(os.path.join(save_dir, html_filename), "wb") as f:
        f.write(snapshot["file"])

    # Save decoded UTF-8 version of HTML
    decoded_content = snapshot["file"].decode(snapshot["encoding"], errors="replace")
    with open(
        os.path.join(save_dir, f"{snapshot['digest']}_utf8.html"), "w", encoding="utf-8"
    ) as f:
        f.write(decoded_content)

    # Save encoding information
    with open(os.path.join(save_dir, "encoding.txt"), "w") as f:
        f.write(snapshot["encoding"])


##################
##### PART 4 #####
##################


def find_and_copy_cached_snapshot(cached_snapshot_dir: str, save_dir: str) -> bool:
    """Find and copy a cached snapshot to a directory if it exists. Return True if a snapshot was found and copied."""
    if os.path.exists(cached_snapshot_dir):
        files = os.listdir(cached_snapshot_dir)
        # If no files, return False
        if not files:
            return False
        for filename in files:
            src = os.path.join(cached_snapshot_dir, filename)
            dst = os.path.join(save_dir, filename)
            # If file already exists, copy it to the save_dir
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
                fdst.write(fsrc.read())
        return True
    return False


##################
##### PART 5 #####
##################

from bs4 import BeautifulSoup


def detect_and_save_frame_tag_attrs(
    soup: BeautifulSoup,
    website_dir: str,
) -> list[dict]:
    """Find all frame tag with their attribute and return a list of dicts"""
    all_frame_tags = soup.find_all("frame")
    frame_tag_attrs = [frame.attrs for frame in all_frame_tags]
    with open(os.path.join(website_dir, "frame_tags.json"), "w") as f:
        json.dump(frame_tag_attrs, f)

    return frame_tag_attrs


##################
##### PART 6 #####
##################


def retrieve_saved_frame_tags_with_parent_info() -> list[dict]:
    """Retrieve all the saved frame tags for a given website directory
    Returns a list of dicts with the following keys:
    - website_dir: the directory of the website
    - website: the website name
    - cdx_entry: the CDX entry of the website
    - frame_tag: the frame tag
    """
    all_frame_tags = []
    all_website_entries = retrieve_saved_website_entries()
    for entry in all_website_entries:
        website = entry["website"]
        website_dir = entry["snapshot_dir"]
        cdx_entry = entry["cdx_entry"]
        frame_tags_path = os.path.join(website_dir, "frame_tags.json")
        try:
            with open(frame_tags_path, "r") as f:
                frame_tags = json.load(f)
                frame_tags_with_dir = [
                    {
                        "website_dir": website_dir,
                        "website": website,
                        "parent_cdx_entry": cdx_entry,
                        "frame_tag": frame_tag,
                    }
                    for frame_tag in frame_tags
                ]
                all_frame_tags.extend(frame_tags_with_dir)
        except Exception as e:
            print(f"Error loading frame tags for {website}: {e}")
            continue
    return all_frame_tags


##################
##### PART 7 #####
##################


def url_to_filename(url: str) -> str:
    """Convert a URL into a safe filename by replacing invalid characters with underscores"""
    # Remove protocol and split on slashes
    url = url.split("://")[-1].replace("/", "_")
    # Replace any remaining invalid characters with underscores
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in url)


##################
##### PART 8 #####
##################


@retry
def query_wm_cdx_closest_entry(url: str, timestamp: str) -> dict | None:
    """Get the closest snapshot entry for a given URL and timestamp"""
    cdx_url = f"https://web.archive.org/cdx/search/cdx?limit=1&sort=closest&url={url}&closest={timestamp}"

    response = requests.get(cdx_url, timeout=30)
    response.raise_for_status()

    entries = parse_wm_cdx_api_response_str(response.text)
    return entries[0] if entries else None


##################
##### PART 9 #####
##################


def retrieve_saved_website_and_frame_entries() -> list[dict]:
    """Retrieve all the saved frame tags for a given website directory
    Returns a list of dicts with the following keys:
    - website_dir: the directory of the website
    - website: the website name
    - cdx_entry: the CDX entry of the website
    - type: "website" or "frame"
    """
    all_website_and_frame_entries = []
    all_website_entries = retrieve_saved_website_entries()
    for entry in all_website_entries:
        website = entry["website"]
        website_dir = entry["snapshot_dir"]
        cdx_entry = entry["cdx_entry"]
        # Add the website entry
        all_website_and_frame_entries.append(
            {
                "website_dir": website_dir,
                "website": website,
                "cdx_entry": cdx_entry,
                "type": "website",
            }
        )

        # Add the frame entries
        frames_dir = os.path.join(website_dir, "frames")

        # If frames directory does not exist, skip
        if not os.path.exists(frames_dir):
            continue

        for frame_name in os.listdir(frames_dir):
            frame_cdx_entry_path = os.path.join(
                frames_dir, frame_name, "cdx_entry.json"
            )
            try:
                with open(frame_cdx_entry_path, "r") as f:
                    frame_cdx_entry = json.load(f)
                frame_dir = os.path.join(frames_dir, frame_name)
                all_website_and_frame_entries.append(
                    {
                        "website_dir": frame_dir,
                        "website": website,
                        "cdx_entry": frame_cdx_entry,
                        "type": "frame",
                    }
                )
            except FileNotFoundError:
                continue
    return all_website_and_frame_entries


###################
##### PART 10 #####
###################

import urllib.parse


def detect_and_save_image_tag_attrs(
    soup: BeautifulSoup, website_dir: str, parent_cdx_entry: dict
) -> list[dict]:
    """Detect all images in a BeautifulSoup object and return a list of dicts"""
    image_tags = []
    for img in soup.find_all("img"):
        image_tag_attrs = img.attrs
        if img.parent.name == "a":
            image_tag_attrs["parent_href"] = img.parent["href"]
            if img.parent["href"].startswith("http"):
                image_tag_attrs["full_parent_href"] = img.parent["href"]
            else:
                image_tag_attrs["full_parent_href"] = urllib.parse.urljoin(
                    parent_cdx_entry["original"], img.parent["href"]
                )
        image_tags.append(image_tag_attrs)
    with open(os.path.join(website_dir, "image_tags.json"), "w") as f:
        json.dump(image_tags, f)

    return image_tags


###################
##### PART 11 #####
###################


def check_banner_properties(width: int, height: int) -> dict:
    """Reference to the IAB and JIAA banner ad sizes in iab-banner-ad-dimensions.csv and jiaa-banner-ad-dimensions.csv"""
    IAB_SIZES = {
        (300, 250): "Medium Rectangle",
        (250, 250): "Square Pop-Up",
        (240, 400): "Vertical Rectangle",
        (336, 280): "Large Rectangle",
        (180, 150): "Rectangle",
        (468, 60): "Full Banner",
        (234, 60): "Half Banner",
        (88, 31): "Micro Button",
        (120, 90): "Button 1",
        (120, 60): "Button 2",
        (120, 240): "Vertical Banner",
        (125, 125): "Square Button",
        (728, 90): "Leaderboard",
        (160, 600): "Wide Skyscraper",
        (120, 600): "Skyscraper",
        (300, 600): "Half Page Ad",
    }

    JIAA_SIZES = {
        (224, 33): "Small Banner",
        (468, 60): "Regular Banner",
        (728, 90): "Large Banner",
        (120, 60): "Small Badge",
        (120, 90): "Regular Badge",
        (125, 125): "Large Badge",
        (200, 200): "Small Rectangle",
        (300, 250): "Regular Rectangle",
        (336, 280): "Large Rectangle",
        (120, 600): "Regular Skyscraper",
        (160, 600): "Wide Skyscraper",
        (148, 800): "Large Skyscraper",
    }

    iab_size = IAB_SIZES.get((width, height), None)
    jiaa_size = JIAA_SIZES.get((width, height), None)
    is_banner_ad = iab_size is not None or jiaa_size is not None
    return {
        "iab_size": iab_size,
        "jiaa_size": jiaa_size,
        "is_banner_ad": is_banner_ad,
    }


###################
##### PART 12 #####
###################


def retrieve_saved_image_tags_with_parent_info() -> list[dict]:
    """Retrieve all the saved image tags for all the website and frame entries
    Returns a list of dicts with the following keys:
    - website_dir: the directory of the website
    - website: the website name
    - cdx_entry: the CDX entry of the website
    - image_tag: the image tag
    """
    all_website_and_frame_entries = retrieve_saved_website_and_frame_entries()
    all_image_tags_with_parent_info = []
    for entry in all_website_and_frame_entries:
        website = entry["website"]
        website_dir = entry["website_dir"]
        cdx_entry = entry["cdx_entry"]
        image_tags_path = os.path.join(website_dir, "image_tags.json")

        try:
            with open(image_tags_path, "r") as f:
                image_tags = json.load(f)
                all_image_tags_with_parent_info.extend(
                    [
                        {
                            "website_dir": website_dir,
                            "website": website,
                            "cdx_entry": cdx_entry,
                            "image_tag": image_tag,
                        }
                        for image_tag in image_tags
                    ]
                )
        except FileNotFoundError:
            continue
    return all_image_tags_with_parent_info


###################
##### PART 13 #####
###################

image_extensions = [
    "jpg",
    "jpeg",
    "png",
    "gif",
    "svg",
    "webp",
    "bmp",
    "ico",
    "tiff",
    ".tif",
]


def get_image_file_extension(cdx_entry: dict) -> str:
    """Get the file extension from a URL or mime type
    Returns a string with the file extension, or None if the extension is not in the list
    """

    # Remove query parameters after ? or #
    url_extension = cdx_entry["original"].split("?")[0].split("#")[0].lower()
    url_extension = url_extension.split(".")[-1]

    # Incase the extension is not in the list, set it to None
    if url_extension not in image_extensions:
        url_extension = None

    # If the mime type is an image, get the extension from the mime type
    mime_type = cdx_entry["mimetype"]
    if mime_type.startswith("image/"):
        mime_type_extension = mime_type.split("/")[1]
        if mime_type_extension not in image_extensions:
            mime_type_extension = None
    else:
        mime_type_extension = None

    # Prefer the extension from the URL, if not, use the extension from the mime type
    return url_extension or mime_type_extension


@retry
def download_image_snapshot(cdx_entry: dict) -> dict:
    """Download an image snapshot from the Wayback Machine
    Returns a dict with the following keys:
    - digest: the digest of the image
    - file: the image file
    - extension: the extension of the image
    """
    wayback_url = f"https://web.archive.org/web/{cdx_entry['timestamp']}im_/{cdx_entry['original']}"
    response = requests.get(wayback_url, timeout=30)
    response.raise_for_status()
    extension = get_image_file_extension(cdx_entry)
    return {
        "digest": cdx_entry["digest"],
        "file": response.content,
        "extension": extension,
    }


def save_image_snapshot(img_snapshot: dict, save_dir: str):
    """Save an image to a directory"""
    os.makedirs(save_dir, exist_ok=True)
    img_filename = f"{img_snapshot['digest']}.{img_snapshot['extension']}"
    img_path = os.path.join(save_dir, img_filename)
    print("Image filename:")
    print(img_filename)
    print(f"Saving image to {img_path}")
    with open(img_path, "wb") as f:
        f.write(img_snapshot["file"])


###################
##### PART 14 #####
###################
from PIL import Image


def get_image_metadata(image_path: str) -> dict:
    """Get the metadata of an image
    Returns a dict with the following keys:
    - width: the width of the image
    - height: the height of the image
    - size: the size of the image
    - animated: whether the image is animated
    - frame_count: the number of frames in the image
    - animation_duration: the duration of the animation
    - loop_count: the number of times the animation loops
    - iab_size: the IAB banner category (if fits)
    - jiaa_size: the JIAA banner category (if fits)
    - corrupt: whether the image is corrupt
    """

    metadata = {
        "width": None,
        "height": None,
        "size": None,
        "animated": None,
        "frame_count": None,
        "animation_duration": None,
        "loop_count": None,
        "iab_size": None,
        "jiaa_size": None,
        "corrupt": True,
    }
    try:
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
                "corrupt": False,
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
            # Check if image is a banner ad
            banner_metadata = check_banner_properties(
                metadata["width"], metadata["height"]
            )

            metadata["iab_size"] = banner_metadata["iab_size"]
            metadata["jiaa_size"] = banner_metadata["jiaa_size"]
    except Exception as e:
        print(f"Error getting image metadata: {e}")

    return metadata

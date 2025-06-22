import os, csv, json, time, requests, urllib.parse
from tenacity import retry, stop_after_attempt, wait_exponential
from bs4 import BeautifulSoup

#####################
##### CONSTANTS #####
#####################

OUTPUT_DIR = "wm_scraping"
os.makedirs(OUTPUT_DIR, exist_ok=True)

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


# Calculate total number of snapshots across all websites
total_snapshots = sum(len(entries) for entries in all_website_entries.values())
print(
    f"Found {len(all_website_entries)} websites with {total_snapshots} total snapshots"
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


@retry(stop=stop_after_attempt(100), wait=wait_exponential(multiplier=1, min=2, max=64))
def download_snapshot(cdx_entry: dict) -> dict:
    wayback_url = f"https://web.archive.org/web/{cdx_entry['timestamp']}id_/{cdx_entry['original']}"

    response = requests.get(wayback_url, timeout=30)
    response.encoding = response.apparent_encoding
    response.raise_for_status()
    return {
        "file": response.content,
        "encoding": response.encoding,
    }


@retry(stop=stop_after_attempt(100), wait=wait_exponential(multiplier=1, min=2, max=64))
def download_image(cdx_entry: dict) -> bytes:
    wayback_url = f"https://web.archive.org/web/{cdx_entry['timestamp']}im_/{cdx_entry['original']}"
    response = requests.get(wayback_url, timeout=30)
    response.raise_for_status()
    return response.content


@retry(stop=stop_after_attempt(100), wait=wait_exponential(multiplier=1, min=2, max=64))
def query_wm_cdx_closest_entry(url: str, timestamp: str) -> dict | None:
    """Get the closest snapshot entry for a given URL and timestamp"""
    cdx_url = f"https://web.archive.org/cdx/search/cdx?url={url}&closest={timestamp}"

    response = requests.get(cdx_url, timeout=30)
    response.raise_for_status()

    entries = parse_wm_cdx_api_response_str(response.text)
    return entries[0] if entries else None


def save_website_snapshot(website: str, cdx_entry: dict, snapshot: dict):
    """Save a website snapshot with the folder structure"""
    # Create website directory
    website_dir = os.path.join(OUTPUT_DIR, website, cdx_entry["timestamp"])
    os.makedirs(website_dir, exist_ok=True)

    # Save main HTML file (original encoding)
    html_filename = f"{cdx_entry['digest']}.html"
    html_path = os.path.join(website_dir, html_filename)
    with open(html_path, "wb") as f:
        f.write(snapshot["file"])

    # Save decoded UTF-8 version of HTML
    decoded_content = snapshot["file"].decode(snapshot["encoding"], errors="replace")
    utf8_html_filename = f"{cdx_entry['digest']}_utf8.html"
    utf8_html_path = os.path.join(website_dir, utf8_html_filename)
    with open(utf8_html_path, "w", encoding="utf-8") as f:
        f.write(decoded_content)

    # Save encoding information
    encoding_path = os.path.join(website_dir, "encoding.txt")
    with open(encoding_path, "w") as f:
        f.write(snapshot["encoding"])

    return website_dir, html_path


def capture_website_resources(website_dir: str, cdx_entry: dict):
    utf8_html_filename = f"{cdx_entry['digest']}_utf8.html"
    utf8_html_path = os.path.join(website_dir, utf8_html_filename)

    with open(utf8_html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
        resources_dir = os.path.join(website_dir, "resources")
        capture_images(resources_dir, cdx_entry, soup)
        capture_frames(resources_dir, cdx_entry, soup)


def capture_images(resources_dir: str, cdx_entry: dict, soup: BeautifulSoup):
    for img in soup.find_all("img"):
        if img["src"].startswith("http"):
            img_url = img["src"]
        else:
            img_url = urllib.parse.urljoin(cdx_entry["original"], img["src"])
        print(img_url)

        closest_entry = query_wm_cdx_closest_entry(img_url, cdx_entry["timestamp"])
        print(closest_entry)

        if not closest_entry:
            print(f"  No closest entry found for {img_url}")
            continue

        image_dir = os.path.join(resources_dir, closest_entry["digest"])
        os.makedirs(image_dir, exist_ok=True)

        if closest_entry["statuscode"] == "200":
            image_content = download_image(closest_entry)
            file_extension = img["src"].split(".")[-1]
            image_filename = f"{closest_entry['digest']}.{file_extension}"
            image_path = os.path.join(image_dir, image_filename)
            with open(image_path, "wb") as f:
                f.write(image_content)

        cdx_entry_path = os.path.join(image_dir, "cdx_entry.json")
        with open(cdx_entry_path, "w") as f:
            json.dump(closest_entry, f)

        time.sleep(1)


def capture_frames(resources_dir: str, cdx_entry: dict, soup: BeautifulSoup):
    for frame in soup.find_all("frame"):
        if frame["src"].startswith("http"):
            frame_url = frame["src"]
        else:
            frame_url = urllib.parse.urljoin(cdx_entry["original"], frame["src"])
        print(frame_url)

        closest_entry = query_wm_cdx_closest_entry(frame_url, cdx_entry["timestamp"])
        print(closest_entry)

        if not closest_entry:
            print(f"  No closest entry found for {frame_url}")
            continue

        frame_dir = os.path.join(resources_dir, closest_entry["digest"])
        os.makedirs(frame_dir, exist_ok=True)

        if closest_entry["statuscode"] == "200":
            frame_content = download_snapshot(closest_entry)
            frame_filename = f"{closest_entry['digest']}.html"
            frame_path = os.path.join(frame_dir, frame_filename)
            with open(frame_path, "wb") as f:
                f.write(frame_content["file"])

            # Save decoded UTF-8 version of HTML
            decoded_content = frame_content["file"].decode(
                frame_content["encoding"], errors="replace"
            )
            utf8_html_filename = f"{closest_entry['digest']}_utf8.html"
            utf8_html_path = os.path.join(frame_dir, utf8_html_filename)
            with open(utf8_html_path, "w", encoding="utf-8") as f:
                f.write(decoded_content)

            # Save encoding information
            encoding_path = os.path.join(frame_dir, "encoding.txt")
            with open(encoding_path, "w") as f:
                f.write(frame_content["encoding"])

        cdx_entry_path = os.path.join(frame_dir, "cdx_entry.json")
        with open(cdx_entry_path, "w") as f:
            json.dump(closest_entry, f)

        print(f"  Captured frame {frame_url} from {cdx_entry['timestamp']}")

        time.sleep(1)

        capture_website_resources(frame_dir, closest_entry)


for website, entries in all_website_entries.items():
    print(f"Found {len(entries)} snapshots for {website}")

    # Download ALL entries for each website
    for cdx_entry in entries:
        # if (
        #     cdx_entry["timestamp"] != "20000510010756"
        #     or cdx_entry["digest"] != "ICIHCOHRGJ6XSKPJQWQ2QWULT7CUPGBO"
        # ):
        #     continue

        print(f"Found {cdx_entry['timestamp']} {cdx_entry['digest']}")

        website_dir = os.path.join(OUTPUT_DIR, website, cdx_entry["timestamp"])

        # Check if snapshot has already been downloaded
        utf8_html_filename = f"{cdx_entry['digest']}_utf8.html"
        utf8_html_path = os.path.join(website_dir, utf8_html_filename)

        if not os.path.exists(utf8_html_path):
            print(f"  Skipping {cdx_entry['timestamp']} - not downloaded")
            continue

        capture_website_resources(website_dir, cdx_entry)

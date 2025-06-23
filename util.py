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


def get_saved_website_entries() -> dict:
    """Get all the saved website entries
    dict: {website: [cdx_entry, ...], website2: [cdx_entry, ...], ...}
    """
    all_website_entries = {}

    for website in os.listdir(OUTPUT_DIR):
        website_dir = os.path.join(OUTPUT_DIR, website)
        all_website_entries[website] = []

        for timestamp_dir in os.listdir(website_dir):
            if os.path.isdir(os.path.join(website_dir, timestamp_dir)):
                cdx_meta_path = os.path.join(
                    website_dir, timestamp_dir, "cdx_entry.json"
                )
                with open(cdx_meta_path, "r") as f:
                    cdx_entry = json.load(f)
                all_website_entries[website].append(cdx_entry)

    return all_website_entries


##################
##### PART 3 #####
##################


@retry
def download_website_snapshot(cdx_entry: dict) -> dict:
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
        for filename in os.listdir(cached_snapshot_dir):
            src = os.path.join(cached_snapshot_dir, filename)
            dst = os.path.join(save_dir, filename)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
                fdst.write(fsrc.read())
        return True
    return False

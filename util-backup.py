import requests, os, json, time, tenacity

OUTPUT_DIR = "data"
CACHE_DIR = "cache"

#####################
##### UTIL #####
#####################

retry = tenacity.retry(
    stop=tenacity.stop_after_attempt(10),
    wait=tenacity.wait_exponential(multiplier=1, min=2, max=32),
    after=lambda _: time.sleep(2),
)


def url_to_filename(url: str) -> str:
    """Convert a URL into a safe filename by replacing invalid characters with underscores"""
    # Remove protocol and split on slashes
    url = url.split("://")[-1].replace("/", "_")
    # Replace any remaining invalid characters with underscores
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in url)


#####################
##### CDX API #####
#####################


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


@retry
def query_wm_cdx_closest_entry(url: str, timestamp: str) -> dict | None:
    """Get the closest snapshot entry for a given URL and timestamp"""
    cdx_url = f"https://web.archive.org/cdx/search/cdx?url={url}&closest={timestamp}"

    response = requests.get(cdx_url, timeout=30)
    response.raise_for_status()

    entries = parse_wm_cdx_api_response_str(response.text)
    return entries[0] if entries else None


#####################
##### DOWNLOAD  #####
#####################


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


@retry
def download_image(cdx_entry: dict) -> dict:
    wayback_url = f"https://web.archive.org/web/{cdx_entry['timestamp']}im_/{cdx_entry['original']}"
    response = requests.get(wayback_url, timeout=30)
    response.raise_for_status()
    file_extension = cdx_entry["original"].split(".")[-1]
    return {
        "digest": cdx_entry["digest"],
        "file": response.content,
        "file_extension": file_extension,
    }


#####################
##### CACHE #####
#####################


def find_and_copy_cached_snapshot(cached_snapshot_dir: str, save_dir: str):
    """Find and copy a cached snapshot to a directory if it exists"""
    if os.path.exists(cached_snapshot_dir):
        for filename in os.listdir(cached_snapshot_dir):
            src = os.path.join(cached_snapshot_dir, filename)
            dst = os.path.join(save_dir, filename)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
                fdst.write(fsrc.read())
        return True
    return False


#####################
##### SAVE #####
#####################


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


def save_image(img_snapshot: dict, save_dir: str):
    """Save an image to a directory"""
    os.makedirs(save_dir, exist_ok=True)
    img_filename = f"{img_snapshot['digest']}.{img_snapshot['file_extension']}"
    img_path = os.path.join(save_dir, img_filename)
    with open(img_path, "wb") as f:
        f.write(img_snapshot["file"])

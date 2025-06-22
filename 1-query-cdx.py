import os, csv, json, time, requests
from tenacity import retry, stop_after_attempt, wait_exponential


#####################
##### CONSTANTS #####
#####################

OUTPUT_DIR = "wm_scraping"
os.makedirs(OUTPUT_DIR, exist_ok=True)

categories_of_interest = ["portal", "content"]

japanese_websites = []
with open("nikkeibp-may2000.csv", "r") as file:
    reader = csv.DictReader(file)
    for row in reader:
        if (
            row.get("is_japanese") == "true"
            and row.get("category") in categories_of_interest
        ):
            japanese_websites.append(row["website"])

print(f"Found {len(japanese_websites)} Japanese websites to scrape")


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


@retry(stop=stop_after_attempt(10), wait=wait_exponential(multiplier=1, min=2, max=8))
def query_wm_cdx_entries(
    url: str,
    from_time: str = "20000501000000",
    to_time: str = "20000531235959",
):
    cdx_url = f"https://web.archive.org/cdx/search/cdx?url={url}&from={from_time}&to={to_time}"

    response = requests.get(cdx_url, timeout=30)
    response.raise_for_status()

    return parse_wm_cdx_api_response_str(response.text)


for website in japanese_websites:
    print(f"Querying CDX for {website}")

    website_dir = os.path.join(OUTPUT_DIR, website)
    if os.path.exists(website_dir):
        print(f"  Skipping - folder already exists")
        continue

    cdx_entries = query_wm_cdx_entries(website)

    print(f"  Found {len(cdx_entries)} CDX entries")
    os.makedirs(website_dir, exist_ok=True)

    # Create folder structure for all entries of this website
    if cdx_entries:
        for cdx_entry in cdx_entries:
            website_timestamp_dir = os.path.join(website_dir, cdx_entry["timestamp"])
            os.makedirs(website_timestamp_dir, exist_ok=True)

            cdx_entry_path = os.path.join(website_timestamp_dir, "cdx_entry.json")
            with open(cdx_entry_path, "w") as f:
                json.dump(cdx_entry, f, indent=2)

        print(f"  Created {len(cdx_entries)} snapshot entry folders")

    time.sleep(1)  # Be respectful to the API

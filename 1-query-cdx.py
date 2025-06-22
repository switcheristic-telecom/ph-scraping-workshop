import os, csv, json
import util

OUTPUT_DIR = "data"
os.makedirs(OUTPUT_DIR, exist_ok=True)


################
##### MAIN #####
################


CATEGORY_OF_INTEREST = ["portal", "content"]

japanese_websites = []
with open("nikkeibp-may2000.csv", "r") as file:
    reader = csv.DictReader(file)
    for row in reader:
        if (
            row.get("is_japanese") == "true"
            and row.get("category") in CATEGORY_OF_INTEREST
        ):
            japanese_websites.append(row["website"])

print(f"Found {len(japanese_websites)} Japanese websites to scrape")


for website in japanese_websites:
    print(f"Querying CDX for {website}")

    website_dir = os.path.join(OUTPUT_DIR, website)
    if os.path.exists(website_dir):
        print(f"  Skipping - folder already exists")
        continue

    cdx_entries = util.query_wm_cdx_entries(website)

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

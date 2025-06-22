import utils, sqlite3
from datetime import datetime

DB_NAME = "wm_scraping.db"

conn = sqlite3.connect(DB_NAME)

cursor = conn.execute(
    "SELECT website FROM source_websites WHERE has_queried_cdx = FALSE"
)
source_websites = cursor.fetchall()

print(f"Found {len(source_websites)} source websites to query")


for source_website in source_websites:
    source_website_str = source_website[0]
    print(f"Querying CDX entries for {source_website_str}")

    cdx_entries = utils.query_wm_cdx_entries(
        source_website_str,
        datetime(2000, 5, 1),
        datetime(2000, 5, 31),
    )

    # Insert all CDX entries for this website
    for cdx_entry in cdx_entries:
        conn.execute(
            "INSERT OR IGNORE INTO cdx_entries (urlkey, timestamp, original, mimetype, statuscode, digest, length, is_source_website, source_website_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                cdx_entry.urlkey,
                cdx_entry.timestamp,
                cdx_entry.original,
                cdx_entry.mimetype,
                cdx_entry.statuscode,
                cdx_entry.digest,
                cdx_entry.length,
                True,
                source_website_str,
            ),
        )

    print(f"Added {len(cdx_entries)} CDX entries for {source_website_str}")

    # Update the source website status
    conn.execute(
        "UPDATE source_websites SET has_queried_cdx = TRUE WHERE website = ?",
        (source_website_str,),
    )

    # Commit the transaction for this website
    conn.commit()
    print(f"Updated source website {source_website_str} to has_queried_cdx = TRUE")


conn.close()

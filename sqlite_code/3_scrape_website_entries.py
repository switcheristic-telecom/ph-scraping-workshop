import utils, sqlite3
from datetime import datetime

DB_NAME = "wm_scraping.db"

conn = sqlite3.connect(DB_NAME)
conn.row_factory = sqlite3.Row  # Enable column access by name

# get one cdx_entries_source_websites, where it's digest is not in the snapshot_files table
cursor = conn.execute(
    "SELECT * FROM cdx_entries WHERE is_source_website = TRUE AND digest NOT IN (SELECT digest FROM snapshot_files) GROUP BY digest"
)
rows = cursor.fetchall()

# Convert rows to CDXSnapshotEntry objects
cdx_entries = [utils.row_to_cdx_entry(row) for row in rows]

print(f"Found {len(cdx_entries)} cdx_entries (source websites) to scrape")
# Now you can access cdx_entries as proper CDXSnapshotEntry objects
for entry in cdx_entries:
    print(f"Downloading snapshot for {entry.original} from {entry.timestamp}")
    downloaded_snapshot = utils.download_snapshot(entry)
    utils.add_snapshot_file(conn, downloaded_snapshot)
    print(f"Added snapshot for {entry.original} from {entry.timestamp}")

conn.close()

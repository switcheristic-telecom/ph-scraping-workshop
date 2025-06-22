import sqlite3

DB_NAME = "wm_scraping.db"

###########################
##### Create database #####
###########################

conn = sqlite3.connect(DB_NAME)

#########################
##### Create tables #####
#########################

# source websites table (website to scrape)
conn.execute(
    "CREATE TABLE IF NOT EXISTS source_websites (website TEXT, has_queried_cdx BOOLEAN DEFAULT FALSE, PRIMARY KEY (website))"
)

# cdx entries for all url (websites / media files)
# `is_source_website` is used to indicate if the url is a website from the source websites table
# `source_website_url` is used to record the url of the source website, if the url is a website from the source websites table
# the data structure is the same as the `CDXSnapshotEntry` class, reflecting the CDX API response
conn.execute(
    "CREATE TABLE IF NOT EXISTS cdx_entries (urlkey TEXT, timestamp DATETIME, original TEXT, mimetype TEXT, statuscode INTEGER, digest TEXT, length INTEGER, is_source_website BOOLEAN, source_website_url TEXT NULL, PRIMARY KEY (digest))"
)

# snapshot files (the actual snapshot files)
conn.execute(
    "CREATE TABLE IF NOT EXISTS snapshot_files (digest TEXT, mimetype TEXT, statuscode INTEGER, length INTEGER, file BLOB, encoding TEXT, has_scraped_for_children BOOLEAN DEFAULT FALSE, PRIMARY KEY (digest))"
)

# snapshot references table (to record the parent-child relationship between snapshots)
conn.execute(
    "CREATE TABLE IF NOT EXISTS snapshot_references (parent_digest TEXT, child_digest TEXT, PRIMARY KEY (parent_digest, child_digest))"
)

conn.close()

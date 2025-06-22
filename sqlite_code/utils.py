############################
##### Helper functions #####
############################

from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential


def str_to_datetime(timestamp_str: str) -> datetime:
    """
    Parse the Wayback Machine timestamp string into a datetime object
    Example: 20001202003400 -> datetime(2000, 12, 02, 00, 34, 00)
    """
    return datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")


def datetime_to_str(dt: datetime) -> str:
    """
    Convert a datetime object to a string in the format of %Y%m%d%H%M%S
    Example: datetime(2000, 12, 02, 00, 34, 00) -> "20001202003400"
    """
    return dt.strftime("%Y%m%d%H%M%S")


#####################################
##### List of Japanese websites #####
#####################################

import csv


def get_japanese_websites() -> list[str]:
    """
    Get the list of Japanese websites from the Nikkei BP May 2000 CSV file
    """
    japanese_websites: list[str] = []
    with open("nikkeibp-may2000.csv", "r") as file:
        reader = csv.reader(file)
        for row in reader:
            if row[2] == "true":
                japanese_websites.append(row[1])

    return japanese_websites


#############################################
##### Wayback Machine CDX API functions #####
#############################################

import requests
from dataclasses import dataclass

CDX_BASE_URL = "https://web.archive.org/cdx/search/cdx"


@dataclass
class CDXSnapshotEntry:
    """
    A class to represent a Wayback Machine snapshot entry
    """

    source_website: str  # the source website that was queried
    # the fields from the CDX API response
    urlkey: str
    timestamp: datetime
    original: str
    mimetype: str
    statuscode: str
    digest: str
    length: str


def parse_wm_cdx_api_response(
    response: str, source_website: str
) -> list[CDXSnapshotEntry]:
    """
    Parse the response from the Wayback Machine CDX API
    """
    entries = [entry for entry in response.strip().split("\n") if entry != ""]
    result = []
    for entry in entries:
        fields = entry.split(" ")
        result.append(
            CDXSnapshotEntry(
                source_website=source_website,
                urlkey=fields[0],
                timestamp=str_to_datetime(fields[1]),
                original=fields[2],
                mimetype=fields[3],
                statuscode=fields[4],
                digest=fields[5],
                length=fields[6],
            )
        )

    return result


@retry(stop=stop_after_attempt(10), wait=wait_exponential(multiplier=1, min=4, max=10))
def query_wm_cdx_entries(
    url: str,
    from_time: datetime = datetime(2000, 5, 1),
    to_time: datetime = datetime(2000, 5, 31),
) -> list[CDXSnapshotEntry]:
    """
    Query the Wayback Machine CDX API for a given URL and time range
    Example URL: https://web.archive.org/cdx/search/cdx?url=google.com&from=20100101000000&to=20100101000000
    """
    from_time_str = datetime_to_str(from_time)
    to_time_str = datetime_to_str(to_time)

    cdx_url = f"{CDX_BASE_URL}?url={url}&from={from_time_str}&to={to_time_str}"

    response = requests.get(cdx_url)
    if response.status_code != 200:
        raise Exception(f"Error retrieving data for {url}: {response.status_code}")

    return parse_wm_cdx_api_response(response.text, url)


@retry(stop=stop_after_attempt(10), wait=wait_exponential(multiplier=1, min=4, max=10))
def query_wm_cdx_closest_entry(
    url: str, timestamp: datetime
) -> CDXSnapshotEntry | None:
    """
    Get the closest snapshot entry for a given URL and timestamp
    Example URL: https://web.archive.org/cdx/search/cdx?&limit=1&sort=closest&url=google.com&closest=20101010101010
    """
    timestamp_str = datetime_to_str(timestamp)
    cdx_url = f"{CDX_BASE_URL}?&limit=1&sort=closest&url={url}&closest={timestamp_str}"

    response = requests.get(cdx_url)
    if response.status_code != 200:
        raise Exception(f"Error retrieving data for {url}: {response.status_code}")
    entries = parse_wm_cdx_api_response(response.text, url)

    if len(entries) == 0:
        return None

    return entries[0]


#######################
##### Downloading #####
#######################

import requests
from requests.exceptions import RequestException


@dataclass
class Snapshot:
    """
    A class to represent a snapshot.
    - digest: the digest of the snapshot
    - mimetype: the mimetype of the snapshot
    - statuscode: the status code of the snapshot
    - length: the length of the snapshot
    - file: the snapshot file
    - encoding: the encoding of the snapshot
    - has_scraped_for_children: whether the snapshot has been scraped for children
    """

    digest: str
    mimetype: str
    statuscode: str
    length: str
    file: bytes
    encoding: str
    has_scraped_for_children: bool


@retry(stop=stop_after_attempt(10), wait=wait_exponential(multiplier=1, min=4, max=10))
def download_snapshot(
    cdx_entry: CDXSnapshotEntry,
) -> Snapshot:
    """
    Downloads the snapshot file from the Wayback Machine
    """
    timestamp_str = datetime_to_str(cdx_entry.timestamp)
    wayback_url = f"https://web.archive.org/web/{timestamp_str}id_/{cdx_entry.original}"

    try:
        response = requests.get(wayback_url, timeout=10)
        response.encoding = response.apparent_encoding
        response.raise_for_status()

        # check if the snapshot file is a website
        if cdx_entry.mimetype == "text/html":
            has_scraped_for_children = False
        else:
            has_scraped_for_children = True

        return Snapshot(
            digest=cdx_entry.digest,
            mimetype=cdx_entry.mimetype,
            statuscode=cdx_entry.statuscode,
            length=cdx_entry.length,
            file=response.content,
            encoding=response.encoding,
            has_scraped_for_children=has_scraped_for_children,
        )
    except RequestException as e:
        raise RuntimeError(f"Failed to download archive: {e}")


##############################
##### Database functions #####
##############################

import sqlite3

DB_NAME = "wm_scraping.db"


def init_db() -> sqlite3.Connection:
    """
    Initialize the database
    """
    conn = sqlite3.connect(DB_NAME)
    create_tables(conn)
    return conn


def create_tables(conn: sqlite3.Connection):
    """
    Create the tables for the database
    """

    # source websites table (website to scrape)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS source_websites (website TEXT, cdx_queried BOOLEAN DEFAULT FALSE, PRIMARY KEY (website))"
    )

    # cdx entries for all url (websites / media files), `is_source_website` is used to indicate if the url is a website from the source websites table
    # the data structure is the same as the `CDXSnapshotEntry` class, reflecting the CDX API response
    conn.execute(
        "CREATE TABLE IF NOT EXISTS cdx_entries (urlkey TEXT, timestamp DATETIME, original TEXT, mimetype TEXT, statuscode INTEGER, digest TEXT, length INTEGER, is_source_website BOOLEAN, PRIMARY KEY (digest))"
    )

    # snapshot files (the actual snapshot files)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS snapshot_files (digest TEXT, mimetype TEXT, statuscode INTEGER, length INTEGER, file BLOB, PRIMARY KEY (digest))"
    )

    # snapshot references table (to record the parent-child relationship between snapshots)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS snapshot_references (parent_digest TEXT, child_digest TEXT, PRIMARY KEY (parent_digest, child_digest))"
    )


def add_source_website(conn: sqlite3.Connection, website: str):
    """
    Add a source website to the database, if it doesn't already exist.
    """
    conn.execute(
        "INSERT OR IGNORE INTO source_websites (website) VALUES (?)", (website,)
    )
    conn.commit()


def add_source_website_cdx_entry(conn: sqlite3.Connection, cdx_entry: CDXSnapshotEntry):
    """
    Add a CDX entry to the database
    """
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
        ),
    )
    conn.commit()


def add_snapshot_file(conn: sqlite3.Connection, snapshot: Snapshot):
    """
    Add a snapshot file to the database
    """
    conn.execute(
        "INSERT OR IGNORE INTO snapshot_files (digest, mimetype, statuscode, length, file, encoding, has_scraped_for_children) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            snapshot.digest,
            snapshot.mimetype,
            snapshot.statuscode,
            snapshot.length,
            snapshot.file,
            snapshot.encoding,
            snapshot.has_scraped_for_children,
        ),
    )
    conn.commit()


def row_to_cdx_entry(row: sqlite3.Row) -> CDXSnapshotEntry:
    """
    Convert a database row to a CDXSnapshotEntry object
    """
    # Handle timestamp conversion - could be datetime object or string
    timestamp = row["timestamp"]
    if isinstance(timestamp, datetime):
        timestamp_obj = timestamp
    elif isinstance(timestamp, str):
        # Try parsing as ISO format first (from database), then Wayback format
        try:
            timestamp_obj = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            try:
                timestamp_obj = str_to_datetime(timestamp)
            except ValueError:
                # Handle standard datetime format like "1996-11-20 06:53:42"
                timestamp_obj = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    else:
        timestamp_obj = timestamp

    return CDXSnapshotEntry(
        source_website=row["source_website_url"],
        urlkey=row["urlkey"],
        timestamp=timestamp_obj,
        original=row["original"],
        mimetype=row["mimetype"],
        statuscode=str(row["statuscode"]),
        digest=row["digest"],
        length=str(row["length"]),
    )


def row_to_snapshot(row: sqlite3.Row) -> Snapshot:
    """
    Convert a database row to a Snapshot object
    """
    return Snapshot(
        digest=row["digest"],
        mimetype=row["mimetype"],
        statuscode=str(row["statuscode"]),
        length=str(row["length"]),
        file=row["file"],
        encoding=row["encoding"],
        has_scraped_for_children=row["has_scraped_for_children"],
    )


##########################################
##### Media file detection functions #####
##########################################

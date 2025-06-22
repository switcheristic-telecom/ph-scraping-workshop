import utils, sqlite3
from datetime import datetime
from bs4 import BeautifulSoup

DB_NAME = "wm_scraping.db"

conn = sqlite3.connect(DB_NAME)
conn.row_factory = sqlite3.Row  # Enable column access by name

# get one snapshot_files entry where mimetype is 'text/html' and has_scraped_for_children is false
cursor = conn.execute(
    "SELECT * FROM snapshot_files WHERE mimetype = 'text/html' AND has_scraped_for_children = FALSE LIMIT 1"
)

snapshot_file = utils.row_to_snapshot(cursor.fetchone())


# read the snapshot with beautifulsoup
# First decode the binary content using the encoding, then parse with BeautifulSoup
decoded_content = snapshot_file.file.decode(snapshot_file.encoding)
soup = BeautifulSoup(decoded_content, "html.parser")


def find_images(soup: BeautifulSoup) -> list[str]:
    """
    Find all image URLs in the BeautifulSoup object
    """
    images = []
    for img in soup.find_all("img"):
        images.append(img["src"])
    return images


images = find_images(soup)

print(images)


conn.close()

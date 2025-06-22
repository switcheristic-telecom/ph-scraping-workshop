import csv, sqlite3


DB_NAME = "wm_scraping.db"

japanese_websites: list[str] = []
with open("nikkeibp-may2000.csv", "r") as file:
    reader = csv.reader(file)
    for row in reader:
        if row[2] == "true":
            japanese_websites.append(row[1])


conn = sqlite3.connect(DB_NAME)

for website in japanese_websites:
    conn.execute(
        "INSERT OR IGNORE INTO source_websites (website) VALUES (?)", (website,)
    )

conn.commit()

conn.close()

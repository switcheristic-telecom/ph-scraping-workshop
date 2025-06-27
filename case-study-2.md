# Case study

In the rest of this lesson, you will build a dataset of banner ads appearing on popular Japanese-language websites in the year 2000 by scraping the Wayback Machine. 

Banner ads are an early form of graphical advertisement on the web. They often feature obtrusive animations and graphics in a bid for user attention and engagement. Though widely considered a visual and privacy nuisance, banner ads played an important role in shaping the visual landscape of the early commercial web. 

A dataset of banner ads can help researchers in several areas of study, including the history of online advertising, the aesthetics of early web design, the globalization of internet marketing, and the infrastructure of ad delivery networks. However, despite their prevalence in the 1990s and early 2000s web, there are very few systematic datasets of banner ads. In 2023, the authors of this lesson published a banner ad dataset containing 22,915 historical banner ads scraped from archived snapshots of more than 77,000 URLs, which are in turn collected from six printed "Internet directory" books published in mainland China and the United States between 1999 and 2001. The dataset can be browsed on [Banner Depot 2000](http://banner-depot-2000.net), which also features a poetry makre which allows the user to compose found poetry using banner ad frames as verses. 

In the case study, we are going to build a miniature version of that dataset by scraping a small set of archived Japanese-language websites from the year 2000, extracting banner ads, and organizing them into a structured dataset.

## Building a seed URL list to scrape

To begin with, we will need a list of popular Japanese-language web pages to scrape banner ads from. For the purposes of this lesson, we are going to use a list of the top-50 most visited URLs by home Internet users in Japan in May 2000, produced by the Japanese financial media company Nikkei BP. The list was used in a study of e-commerce cultures in the United States and Japan in 2000 by Japanese Internet researcher Kumiko Aoki. 

In the study, Aoki made the following observation about ads on popular Japanese websites in May 2000: 
 - Overall, banner ads are used sparingly. Among  only three sites carried more than five banner ads. 
 - Companies fill their websites with their own banner ads. 

By scraping the dataset, we should be able to verify these claims. In addition, we will be able to see to how well these websites are archived on the Wayback Machine. 

While it should be trivial to manually copy the content of the table to a CSV file, we have prepared the CSV file for you in advance for your convenience. You can download the CSV file, as well as a Python notebook containing all code snippets in the case study section [here](URL:TKTKTKTKTKTK). 

In the CSV file, we removed four websites that do not feature Japanese-language content: microsoft.com (ranked #2), msn.com (ranked #9), real.com (ranked #44), and geocities.com (ranked #46). This leaves us 46 URLs to scrape. 

## Downloading web pages

### Downloading CDX data for each URL

To scrape banner ad images from these URLs, we need to first obtain available snapshots of these URLs on the Wayback Machine. To do this, we will use the CDX Server API. Since the CDX Server API is subject to rate limiting, we will decorate our download function with the tenacity library. Below, we define a reusable `retry` decorator using the tenacity library with these rules: 
 - `stop_after_attempt(10)`: Give up after 10 total tries.
 - `wait_exponential(multiplier=1, min=2, max=64)`: Between retries, wait an exponentially increasing interval: start at 2 seconds, then roughly 4, 8, 16, up to a ceiling of 64 seconds.


```python
import tenacity, time

retry = tenacity.retry(
    stop=tenacity.stop_after_attempt(10),
    wait=tenacity.wait_exponential(multiplier=1, min=2, max=32),
)
```
We will use the `retry` decorator with the scraping functions we will build shortly afterwards. 

In the CDX Server API query, we add the following parameters:
 - `&collapse=digest`: makes the Wayback Machine return only unique snapshot (i.e. adjacent snapshots with the same `digest` is collapsed into the first snapshot, as the ones that follows have the identical content)
 - `&filter=statuscode:200`: makes the Wayback Machine return only successfully captured snapshots. 
 - `&from=20000401000000&to=20000630235959`: makes the Wayback return only snapshots captured from April 1, 2000 to June 30. This period encapsulates the month of May by one month before and after. 

Below is the function for downloading CDX data: 

```python
@retry
def download_cdx_data(url):
    time.sleep(1.5) # Observing the CDX Server rate limit as stipulated in the Github post cited above. 
    cdx_url = f"https://web.archive.org/cdx/search/cdx?url={url}&from=20000401000000&to=20000630235959&filter=statuscode:200&collapse=digest"
    print(f"Fetching CDX data for: {url}")
    response = requests.get(cdx_url, timeout=10)
    response.raise_for_status()

    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"Failed to fetch CDX data for {url}: {response.status_code}")
```

Then, we will loop through all URLs in the CSV file, and download the CDX data for each URL. 

As URLs tend to contain special characters such as slashes that may not be used in file names on most operating systems, we are going to calculate a [MD5 hash](https://en.wikipedia.org/wiki/MD5) for each URL in the list, and use the hash to identify URLs in our dataset. 

```python

# load nikkeibp-may2000-abridged.csv
import csv
import hashlib
from pathlib import Path

csv_file = "nikkeibp-may2000-abridged.csv"

urls_data = []

# Load CSV file into dictionary
with open(csv_file, mode='r', encoding='utf-8') as file:
    reader = csv.DictReader(file)
    urls_data = list(reader)

# Generate a MD5 hash for each URL. 
# We will use this hash for saving the CDX data and HTML data. 

for url in urls_data:
    url['md5'] = hashlib.md5(url['url'].encode('utf-8')).hexdigest()

for url in urls_data: 
    # If the CDX data for the URL has already been downloaded, skip it.
    cdx_file_path = Path(f"data/{url['md5']}/cdx.csv")
    if cdx_file_path.exists():
        print(f"CDX data for {url['url']} already exists at {cdx_file_path}. Skipping download.")
        continue
    try:
        cdx_data = download_cdx_data(url['url'])
        # Save the CDX data to a file named after the MD5 hash of the URL
        cdx_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cdx_file_path, 'w', encoding='utf-8') as cdx_file:
            cdx_file.write(cdx_data)
        print(f"CDX data saved for {url['url']} at {cdx_file_path}")
    except Exception as e:
        print(f"Error fetching CDX data for {url['url']}: {e}")
```

Depending on your Internet connection, the CDX Server API scraping might take 10-20 minutes to finish. You may see multiple attempts at downloading one URL - this is because the tenacity library is managing to retry downloading if a previous attempt has failed. Should the scraping process be interrupted, you should be able to rerun the code, and the code is able to detect any data already downloaded and resume downloading the rest of the data. 

### Downloading archived snapshots

For the purpose of this lesson, we will randomly select two archived snapshots of each website to analyze. The following is a function that parses a downloaded CDX file, and after checking and removing snapshots already downloaded, 

```python
import random
def choose_random_snapshots_to_download(cdx_file_path, num_snapshots=2):

    print(f"Choosing {num_snapshots} random snapshots from {cdx_file_path}")

    # check if there are already any downloaded snapshots
    snapshots_dir = Path(cdx_file_path).parent
    downloaded_htmls = snapshots_dir.glob('*.html')
    # get file names without the extension
    downloaded_htmls = [html_file.stem for html_file in downloaded_htmls]
    print(f"Already downloaded {len(downloaded_htmls)} snapshots for {cdx_file_path}")
    num_snapshots -= len(downloaded_htmls)
    print(f"Number of new snapshots to download: {num_snapshots}")

    if num_snapshots <= 0:
        print(f"No new snapshots to download for {cdx_file_path}. Already have {len(downloaded_htmls)} downloaded.")
        return []
    
    # Read the CDX file and collect snapshots
    snapshots = []
    with open(cdx_file_path, 'r', encoding='utf-8') as cdx_file:
        reader = csv.reader(cdx_file, delimiter=' ')
        for row in reader:
            if len(row) >= 3:  # Ensure there are enough columns
                snapshots.append(row)
    
    # Remove duplicates based on the digest (6th column)
    unique_snapshots = {snapshot[5]: snapshot for snapshot in snapshots}.values()

    # Remove snapshots that have already been downloaded
    unique_snapshots = [snapshot for snapshot in unique_snapshots if snapshot[1] not in downloaded_htmls]
    
    # Randomly select the target number of snapshots
    selected_snapshots = random.sample(list(unique_snapshots), min(num_snapshots, len(unique_snapshots)))
    return selected_snapshots
```
Now, we will use the above function to sample and download snapshots. We will employ the encoding detection mechanism built into the requests library and save all downloaded files in UTF-8 encoding for further processing. 



### Dealing with frames

After we downloaded all snapshots, we can first do a quick check and see if any web pages contain the `<frameset>` element: 

```python


```


### Looking for banner ads on downloaded web pages

After we downloaded all the archived snapshots, we can proceed to identify banner ads in these snapshots. As mentioned earlier, in the 1990s and early 2000s, it was a common practice to provide the `width` and `height` attributes of `<img>` tags. This is good news to us, because it allows us to identify banner ads without downloading all images referenced on the page. 

Soon after the advent of the first banner ads, advertisers and ad networks attempted to standardize banner ad dimensions in a bid to 

The following function analyzes a download HTML file and outputs a list of image URLs from the 

```python
def output
```

## Downloading banner ads and calculating time skew

The following function 

## Data insights

Despite its small size, we can gain some preliminary insights from our dataset. The 


## Building a gallery of Japanese banner ads

As the last step, we will build a simple gallery of 
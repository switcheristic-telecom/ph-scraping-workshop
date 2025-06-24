# Programming Historian: Scraping Media Resources from the Wayback Machine

This repository contains the code and data for a Programming Historian lesson on scraping historical media resources from archived web pages on the Internet Archive's Wayback Machine. The lesson demonstrates how to programmatically access, download, and analyze historical web content, with a case study focused on extracting banner advertisements from popular Japanese websites circa 2000.

## Lesson Overview

This lesson teaches advanced web scraping techniques specifically designed for historical web archives. Unlike scraping live websites, archived web pages present unique challenges including:

- **Time skew**: Resource files may be archived at different timestamps than their parent pages
- **Legacy encoding**: Non-English pages from the 1990s-2000s often use region-specific character encodings
- **URL rewriting**: The Wayback Machine modifies URLs during replay to point to archived versions
- **Legacy media formats**: Historical pages may contain Flash, Shockwave, VRML, and other obsolete formats
- **Nested frame structures**: Recursive resource downloading for frame-based layouts

## Case Study Focus

The lesson builds a dataset of banner advertisements appearing on popular Japanese-language websites from May 2000, using the top-50 most visited websites in Japan from that period. This case study demonstrates practical applications for:

- Digital advertising history research
- Web design evolution studies
- Cultural analysis of early internet commercialization
- Technical archaeology of legacy web formats

## Scripts Overview

### 1. `1-query-cdx.py` - CDX API Query Engine

Queries the Wayback Machine's CDX Server API to discover all available archived snapshots for target websites.

**Key Features:**

- Filters websites by category and language from the input CSV
- Creates organized folder structure for each website and timestamp
- Saves CDX metadata for each discovered snapshot
- Implements server-side filtering to optimize API requests

**Output:** Creates the basic `data/` folder structure with CDX metadata files.

### 2. `2-download-snapshot.py` - Snapshot Downloader

Downloads the actual HTML content for each archived snapshot discovered in step 1.

**Key Features:**

- Downloads original and UTF-8 converted versions of HTML files
- Implements caching mechanism to avoid re-downloading identical content
- Handles legacy character encoding detection and conversion
- Uses exponential backoff retry strategy for rate limiting

**Output:** Populates snapshot directories with HTML files and encoding metadata.

### 3. `3-scrape-resources.py` - Media Resource Extractor

Analyzes downloaded HTML files to identify and download embedded media resources.

**Key Features:**

- Parses HTML using BeautifulSoup to find `<img>` and `<frame>` elements
- Handles recursive frame downloading (frames within frames)
- Resolves relative URLs to absolute paths
- Downloads images, videos, and other media files
- Maintains time-accurate resource selection using closest timestamp matching

**Output:** Creates `resources/` subdirectories containing all media files with metadata.

### 4. `4-summarize-image-resources.py` - Dataset Analysis

Generates comprehensive metadata analysis of all discovered images.

**Key Features:**

- Analyzes image dimensions, file sizes, and formats
- Detects animated GIFs with frame counts and duration
- Identifies potential banner advertisements using IAB and JIAA standard sizes
- Exports complete dataset as CSV for further analysis
- Supports common image formats: JPEG, PNG, GIF, SVG, WebP, BMP, ICO, TIFF

**Output:** Creates `image-summary.csv` with comprehensive image metadata.

### `util.py` - Core Utilities

Provides shared functionality for all scripts including:

- Wayback Machine CDX API interface
- HTTP download with retry logic and rate limiting
- File caching and safe filename generation
- Website snapshot and image saving utilities

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

**Required packages:**

- `requests` - HTTP client for API calls and downloads
- `beautifulsoup4` - HTML parsing and analysis
- `pillow` - Image metadata extraction and analysis
- `tenacity` - Retry logic with exponential backoff

## Usage

Run the scripts in sequence:

```bash
# 1. Discover available snapshots
python 1-query-cdx.py

# 2. Download HTML content
python 2-download-snapshot.py

# 3. Extract media resources
python 3-scrape-resources.py

# 4. Generate analysis dataset
python 4-summarize-image-resources.py
```

## Data Structure

The project creates the following directory structure:

```bash
data/                          # Main output directory
├── website.com/               # One directory per website
│   └── 20000510123456/        # Timestamp-based snapshot directories
│       ├── cdx_entry.json     # CDX metadata for this snapshot
│       ├── [digest].html      # Original HTML (raw encoding)
│       ├── [digest]_utf8.html # UTF-8 converted HTML
│       ├── encoding.txt       # Detected character encoding
│       └── resources/         # Media resources directory
│           ├── image_file.gif/# Resource-specific directories
│           │   ├── cdx_entry.json    # Resource CDX metadata
│           │   └── [digest].gif      # Actual media file
│           ├── frame_content.html/   # Frame resources (recursive)
│           │   ├── cdx_entry.json
│           │   ├── [digest].html
│           │   ├── [digest]_utf8.html
│           │   └── resources/        # Nested resources (recursive)
│           └── [resource].json       # Resource discovery metadata

cache/                         # Shared cache directory
└── [digest]/                  # Content-based caching by Wayback Machine digest
    └── [cached files]         # Cached downloads to avoid duplicate downloads
```

## Key Features

- **Content-based caching**: Uses Wayback Machine digest hashes to avoid downloading identical content multiple times
- **Encoding detection**: Automatically handles legacy character encodings for international content
- **Rate limiting**: Implements respectful crawling with exponential backoff
- **Time-accurate resource matching**: Finds the closest archived version of each resource
- **Recursive frame support**: Handles complex frame-based layouts with nested resources
- **Comprehensive metadata**: Tracks CDX information, timestamps, and content relationships
- **Banner ad detection**: Identifies potential advertisements using standard banner dimensions

## Research Applications

This toolkit enables research into:

- **Digital advertising evolution**: Track banner ad formats, sizes, and design trends
- **Web design history**: Study layout patterns, color schemes, and UI conventions
- **Cultural analysis**: Examine regional differences in web aesthetics and content
- **Technical archaeology**: Preserve and study legacy web technologies
- **Content analysis**: Perform quantitative studies of historical web media

## Ethical Considerations

- Respects Wayback Machine rate limits and terms of service
- Implements reasonable delays between requests
- Caches content to minimize server load
- Focuses on publicly archived, historical content
- Suitable for academic and research purposes

## Limitations

- JavaScript-heavy sites may not render completely (consider Selenium for complex cases)
- Some legacy media formats may not be viewable in modern browsers
- CDX API availability depends on Internet Archive service status
- Time skew may affect historical accuracy of reconstructed pages
- Rate limiting may slow large-scale scraping operations

## About This Repository

This repository serves as the companion code and data for the Programming Historian lesson on advanced web scraping techniques for digital humanities research. It provides working examples and reproducible code for the methods taught in the lesson.

## Further Reading

- [Internet Archive CDX Server API Documentation](https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server)
- [Web Archive Replay and Time Skew](https://arxiv.org/pdf/1402.0928)
- [Programming Historian Web Scraping Lessons](https://programminghistorian.org/en/lessons/?topic=web-scraping)

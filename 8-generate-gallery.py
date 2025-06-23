import os
import csv
import glob
from collections import defaultdict
from datetime import datetime


def find_image_by_digest(digest, data_dir="data"):
    """
    Recursively search for an image file with the given digest name
    """
    # Search for files with the digest name and any extension
    pattern = f"**/{digest}.*"
    matches = glob.glob(os.path.join(data_dir, pattern), recursive=True)

    # Filter to only image files
    image_extensions = {".gif", ".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    for match in matches:
        _, ext = os.path.splitext(match.lower())
        if ext in image_extensions:
            return match

    return None


def format_timestamp(timestamp_str):
    """
    Convert timestamp from YYYYMMDDHHMMSS format to human readable
    """
    if not timestamp_str or len(timestamp_str) != 14:
        return timestamp_str

    try:
        # Parse YYYYMMDDHHMMSS
        year = timestamp_str[:4]
        month = timestamp_str[4:6]
        day = timestamp_str[6:8]
        hour = timestamp_str[8:10]
        minute = timestamp_str[10:12]
        second = timestamp_str[12:14]

        # Create datetime object
        dt = datetime(
            int(year), int(month), int(day), int(hour), int(minute), int(second)
        )

        # Format as readable string
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, IndexError):
        return timestamp_str


def format_time_skew(time_skew_str):
    """
    Convert time_skew from seconds to days (with decimal)
    """
    if not time_skew_str:
        return ""

    try:
        seconds = float(time_skew_str)
        days = seconds / (24 * 60 * 60)  # Convert seconds to days

        if abs(days) >= 1:
            return f"{days:.2f} days"
        elif abs(seconds) >= 3600:
            hours = seconds / 3600
            return f"{hours:.2f} hours"
        elif abs(seconds) >= 60:
            minutes = seconds / 60
            return f"{minutes:.2f} minutes"
        else:
            return f"{seconds:.2f} seconds"
    except (ValueError, TypeError):
        return time_skew_str


def load_banner_data():
    """
    Load and group banner ad data by digest
    """
    data_by_digest = defaultdict(list)

    with open("banner-ads-summary-reference.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            digest = row["digest"]
            data_by_digest[digest].append(row)

    return data_by_digest


def generate_html(gallery_data):
    """
    Generate the complete HTML page in 2000s style
    """
    # Calculate unique websites
    unique_websites = set()
    for item in gallery_data:
        for row in item["rows"]:
            website = row.get("website", "")
            if website:
                unique_websites.add(website)

    unique_website_count = len(unique_websites)
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Banner Ads Gallery - Year 2000 Japanese Websites</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 10px;
            background-color: #ffffff;
        }}
        
        h1 {{
            color: #000080;
            text-align: center;
            font-size: 24px;
        }}
        
        .stats {{
            text-align: center;
            color: #666666;
            margin-bottom: 20px;
            font-size: 14px;
        }}
        
        .main-table {{
            border: 2px solid #000000;
            border-collapse: collapse;
            width: 100%;
            overflow-x: auto;
        }}
        
        .main-table th {{
            background-color: #cccccc;
            color: #000000;
            padding: 8px;
            border: 1px solid #000000;
            text-align: center;
            font-weight: bold;
            white-space: nowrap;
        }}
        
        .main-table td {{
            padding: 8px;
            border: 1px solid #000000;
            vertical-align: top;
            font-size: 12px;
        }}
        
        .main-table tr:nth-child(even) {{
            background-color: #f0f0f0;
        }}
        
        .banner-image {{
            max-width: 200px;
            max-height: 100px;
            border: 1px solid #666666;
        }}
        
        .image-container {{
            text-align: center;
        }}
        
        .digest-caption {{
            font-family: monospace;
            font-size: 9px;
            color: #666666;
            margin-top: 5px;
            background-color: #ffffcc;
            padding: 2px 4px;
            border-radius: 3px;
            word-break: break-all;
            max-width: 200px;
        }}
        
        .metadata-cell {{
            font-size: 10px;
            background-color: #e6f3ff;
            max-width: 200px;
            line-height: 1.3;
        }}
        
        .tag-metadata-cell {{
            font-size: 10px;
            background-color: #f0fff0;
            max-width: 250px;
            line-height: 1.3;
        }}
        
        .url-cell {{
            max-width: 200px;
            word-break: break-all;
            font-size: 11px;
        }}
        
        .timestamp-cell {{
            font-size: 11px;
            white-space: nowrap;
        }}
        
        .website-link {{
            color: #0000ff;
            text-decoration: underline;
        }}
        
        .website-link:visited {{
            color: #800080;
        }}
        
        .center {{
            text-align: center;
        }}
        
        .nowrap {{
            white-space: nowrap;
        }}
        
        .table-container {{
            overflow-x: auto;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <h1>🌐 Banner Ads Gallery 🌐</h1>
    <div class="stats">
        <b>Total unique banner ad image: {len(gallery_data)}</b><br>
        <b>Total unique websites: {unique_website_count}</b>
    </div>
    
    <div class="table-container">
        <table class="main-table" cellpadding="0" cellspacing="0">
            <thead>
                <tr>
                    <th>Banner Image</th>
                    <th>Occurrences</th>
                    <th>Image Metadata</th>
                    <th>Image Tag Metadata</th>
                    <th>Website Wayback Link</th>
                    <th>website</th>
                    <th>website_timestamp</th>
                    <th>timestamp</th>
                    <th>time_skew</th>
                    <th>urlkey</th>
                    <th>original</th>
                    <th>mimetype</th>
                    <th>statuscode</th>
                </tr>
            </thead>
            <tbody>
"""

    for item in gallery_data:
        # Process each occurrence of this image
        for i, row in enumerate(item["rows"]):
            # Create Wayback Machine URL
            website = row.get("website", "")
            website_timestamp = row.get("website_timestamp", "")
            wayback_url = (
                f"https://web.archive.org/web/{website_timestamp}/{website}"
                if website and website_timestamp
                else ""
            )

            # Format timestamps
            formatted_website_timestamp = format_timestamp(website_timestamp)
            formatted_timestamp = format_timestamp(row.get("timestamp", ""))

            # Format time skew
            formatted_time_skew = format_time_skew(row.get("time_skew", ""))

            # Only show image, occurrence count, and image metadata in first row for this digest
            if i == 0:
                # Create image element or error message with digest caption
                if item["image_path"]:
                    image_element = f"""<div class="image-container">
                        <img src="{item["image_path"]}" alt="Banner ad" class="banner-image">
                        <div class="digest-caption">{item["digest"]}</div>
                    </div>"""
                else:
                    image_element = f"""<div class="image-container">
                        <i>Image not found</i>
                        <div class="digest-caption">{item["digest"]}</div>
                    </div>"""

                occurrence_cell = f'<div class="center"><b>{item["count"]}</b></div>'

                # Create image metadata cell with multi-line layout (constant per image)
                first_row = row
                length = first_row.get("length", "")
                if length and length.isdigit():
                    length_kb = round(int(length) / 1024, 1)
                    length_display = f"{length} bytes ({length_kb} KB)"
                else:
                    length_display = length or ""

                metadata_lines = []
                # Always show field names, even if values are empty
                width = first_row.get("width", "")
                height = first_row.get("height", "")
                if width and height:
                    metadata_lines.append(f"<b>Size:</b> {width}×{height}px")
                elif width or height:
                    metadata_lines.append(
                        f"<b>Size:</b> {width or ''}×{height or ''}px"
                    )
                else:
                    metadata_lines.append("<b>Size:</b> ")

                metadata_lines.append(f"<b>File Size:</b> {length_display}")
                metadata_lines.append(
                    f"<b>Display Size:</b> {first_row.get('size', '')}"
                )
                metadata_lines.append(
                    f"<b>Animated:</b> {first_row.get('animated', '')}"
                )
                metadata_lines.append(
                    f"<b>Frames:</b> {first_row.get('frame_count', '')}"
                )

                duration = first_row.get("animation_duration", "")
                if duration:
                    metadata_lines.append(f"<b>Duration:</b> {duration}ms")
                else:
                    metadata_lines.append("<b>Duration:</b> ")

                metadata_lines.append(
                    f"<b>Loops:</b> {first_row.get('loop_count', '')}"
                )
                metadata_lines.append(
                    f"<b>IAB Size:</b> {first_row.get('iab_size', '')}"
                )
                metadata_lines.append(
                    f"<b>JIAA Size:</b> {first_row.get('jiaa_size', '')}"
                )
                metadata_lines.append(f"<b>Corrupt:</b> {first_row.get('corrupt', '')}")

                metadata_cell = (
                    f'<div class="metadata-cell">{"<br>".join(metadata_lines)}</div>'
                )
            else:
                image_element = ""
                occurrence_cell = ""
                metadata_cell = ""

            # Create image tag metadata cell for every row (can vary per occurrence)
            tag_metadata_lines = []

            # Always show field names, even if values are empty
            tag_width = row.get("image_tag_width", "")
            tag_height = row.get("image_tag_height", "")
            if tag_width and tag_height:
                tag_metadata_lines.append(
                    f"<b>Tag Size:</b> {tag_width}×{tag_height}px"
                )
            elif tag_width or tag_height:
                tag_metadata_lines.append(
                    f"<b>Tag Size:</b> {tag_width or ''}×{tag_height or ''}px"
                )
            else:
                tag_metadata_lines.append("<b>Tag Size:</b> ")

            tag_metadata_lines.append(
                f"<b>Tag IAB Size:</b> {row.get('image_tag_banner_iab_size', '')}"
            )
            tag_metadata_lines.append(
                f"<b>Tag JIAA Size:</b> {row.get('image_tag_banner_jiaa_size', '')}"
            )
            tag_metadata_lines.append(
                f"<b>Alt Text:</b> {row.get('image_tag_alt_text', '')}"
            )

            parent_href = row.get("image_tag_parent_href", "")
            if parent_href:
                if len(parent_href) > 50:
                    parent_display = parent_href[:50] + "..."
                else:
                    parent_display = parent_href
                tag_metadata_lines.append(
                    f"<b>Parent Link:</b> <a href='{parent_href}' target='_blank' class='website-link'>{parent_display}</a>"
                )
            else:
                tag_metadata_lines.append("<b>Parent Link:</b> ")

            full_href = row.get("image_tag_full_parent_href", "")
            if full_href:
                if len(full_href) > 50:
                    full_display = full_href[:50] + "..."
                else:
                    full_display = full_href
                tag_metadata_lines.append(
                    f"<b>Full Parent Link:</b> <a href='{full_href}' target='_blank' class='website-link'>{full_display}</a>"
                )
            else:
                tag_metadata_lines.append("<b>Full Parent Link:</b> ")

            tag_metadata_cell = (
                f'<div class="tag-metadata-cell">{"<br>".join(tag_metadata_lines)}</div>'
                if tag_metadata_lines
                else ""
            )

            html += f"""
                <tr>
                    <td class="center">{image_element}</td>
                    <td class="center">{occurrence_cell}</td>
                    <td>{metadata_cell}</td>
                    <td>{tag_metadata_cell}</td>
                    <td class="center">
                        {f'<a href="{wayback_url}" target="_blank" class="website-link">View Page</a>' if wayback_url else ''}
                    </td>
                    <td class="nowrap">{row.get('website', '')}</td>
                    <td class="timestamp-cell">{formatted_website_timestamp}</td>
                    <td class="timestamp-cell">{formatted_timestamp}</td>
                    <td class="nowrap">{formatted_time_skew}</td>
                    <td class="url-cell">{row.get('urlkey', '')}</td>
                    <td class="url-cell">
                        <a href="{row.get('original', '')}" target="_blank" class="website-link">{row.get('original', '')}</a>
                    </td>
                    <td class="nowrap">{row.get('mimetype', '')}</td>
                    <td class="center">{row.get('statuscode', '')}</td>
                </tr>"""

    html += """
            </tbody>
        </table>
    </div>
</body>
</html>"""

    return html


def main():
    """
    Main function to generate the gallery
    """
    print("Loading banner ad data...")
    banner_data = load_banner_data()

    print("Finding image files...")
    gallery_data = []
    for digest, rows in banner_data.items():
        image_path = find_image_by_digest(digest)
        gallery_data.append(
            {
                "digest": digest,
                "image_path": image_path,
                "rows": rows,
                "count": len(rows),
            }
        )

    # Sort by number of occurrences (descending)
    gallery_data.sort(key=lambda x: x["count"], reverse=True)

    print(f"Found {len(gallery_data)} unique images")
    print(
        f"Found actual image files for {sum(1 for item in gallery_data if item['image_path'])} images"
    )

    # Generate HTML
    print("Generating HTML...")
    html_content = generate_html(gallery_data)

    # Write to file
    with open("gallery.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    print("Generated gallery.html successfully!")
    print("Open gallery.html in your browser to view the gallery")


if __name__ == "__main__":
    main()

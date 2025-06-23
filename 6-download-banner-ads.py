import os, json
import util

all_image_tags_with_parent_info = util.get_saved_image_tags_with_parent_info()

print(f"Found {len(all_image_tags_with_parent_info)} image tags")

for image_tag_with_parent_info in all_image_tags_with_parent_info:
    image_tag = image_tag_with_parent_info["image_tag"]
    website = image_tag_with_parent_info["website"]
    website_dir = image_tag_with_parent_info["website_dir"]
    cdx_entry = image_tag_with_parent_info["cdx_entry"]

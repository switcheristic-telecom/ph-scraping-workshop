# Case study

In the rest of this lesson, you will build a dataset of banner ads appearing on popular Japanese-language websites in the year 2000 by scraping the Wayback Machine. 

The banner ad is the earliest form of graphical advertising on the web. Often featuring 

In 2003, the authors of this lesson built [Banner Depot 2000](http://banner-depot-2000.net), an online banner ad archive/database as well as 

Such a dataset can help researchers in several areas, including researchers working on web advertising history, Internet visual culture, and web archive studies itself. 


## Building a seed URL list to scrape

To begin with, we will need a list of popular Japanese-language web pages to scrape banner ads from. We are going to use a list of the top-50 most visited websites by home users in Japan, originally published by the Japanese business media outlet Nikkei BP and preserved as an appendix in a 2000 study about e-commerce cultures in the United States and Japan. 

## Downloading web pages

### Using tenacity to 

Before we start downloading data, we will need to ensure that our scraper can keep running even if a network error or Wayback Machine's rate limiter interrupts the download process. To do this, we use tenacity to decorate 

### Downloading CDX data for each URL

For the purposes of this lesson, we are going to 

### Downloading snapshots of each URL


### Dealing with frames

Before we head into 

### Looking for banner ads on downloaded web pages

The archived HTML files we downloaded in the steps above does not 

As mentioned earlier, in the 1990s and early 2000s, web developers and web authoring software used to manually put image dimension information in the `width` and `height` attributes of `<img>` tags. This information allows us to identify banner ads on a 

Soon after the advent of the first banner ads, advertisers and ad networks attempted to standardize banner ad dimensions in a bid to regulate  

The following function analyzes a download HTML file and outputs a list of image URLs from the 

```python
def output
```

## Downloading banner ads and calculating time skew

The following function 



## Building a gallery of Japanese banner ads


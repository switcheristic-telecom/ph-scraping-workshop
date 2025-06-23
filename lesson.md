<!-- See lesson template: https://programminghistorian.org/en/lesson-template.md -->

---
title: Scraping media resources on archived web pages from the Wayback Machine
collection: lessons  
layout: lesson  
authors:
- Huang, Richard Lewei
- Zhao, Yufeng
---

# A Table of Contents

{% include toc.html %}

--

# Lesson Introduction

In this lesson, you will learn how to scrape media resources from historical web pages archived on the Internet Archive’s Wayback Machine. 

As historians increasingly turn their attention to the 1990s and early 2000s \- a period marked by rapid expansion and mainstream adoption of the web \- the value of web archives as historical sources is gaining wider recognition.  While many web archives like the Wayback Machine provide a user-friendly interface for viewing archived snapshots of a single URL, historians looking to perform computational or quantitative analysis may prefer accessing archived web data programmatically in order to examine the availability of archived snapshots of historical URLs, bulk download archived snapshots, and extract specific page elements for further analysis. 

In this lesson, we will use the Wayback Machine’s CDX Server API to scrape media resources featured on archived snapshots of historical URLs on the Wayback Machine. Specifically, we are going to build a small dataset of historical web banner ads appearing on popular Japanese-language websites in the year 2000. The workflow introduced in the lesson is generally comparable to standard web scraping procedures, but we will cover a number of challenges specific to scraping historical web pages archived on the Wayback Machine - especially non-English web pages from the 1990s and early 2000s. 


# Prerequisites

This lesson is designed for people who have an intermediate understanding of Python and HTML. You should ideally have prior experience with web scraping in Python and BeautifulSoup, as well as a basic understanding of how web archives work, though we are going to cover some of the background information in the next section. 

If you are new to Python and HTML, you may want to consult the following Programming Historian lessons on [Python](https://programminghistorian.org/en/lessons/introduction-and-installation) and [HTML](https://programminghistorian.org/en/lessons/viewing-html-files), and subsequent lessons in that series. You may also want to check out the lesson [Creating APIs with Python and Flask](https://programminghistorian.org/en/lessons/creating-apis-with-python-and-flask) to familiarize yourself with basic concepts related to APIs. 

You can follow the lesson on any mainstream operating system you prefer, including Windows, macOS, and popular Linux distributions, as long as you can get a relatively recent version of Python installed on your operating system. At the time of writing, the most recent Python version is 3.13. On Python, you will need to have the following libraries installed: 

- requests  
- BeautifulSoup  
- pillow  
- tenacity 

We recommend that you install [Anaconda](https://anaconda.org/anaconda/python), a distribution of Python specifically designed for data science research for this lesson. A standard installation of Anaconda includes the first three libraries, and you can easily install tenacity by running `pip install tenacity`. Refer to the Programming Historian course [Installing Python Modules with pip](https://programminghistorian.org/en/lessons/installing-python-modules-pip) for more information.  

# Learning outcomes

By the end of this lesson, you will learn: 

- Using the Wayback Machine CDX Server API to check the available archived snapshots of a given historical URL.    
- Batch downloading archived web page snapshots from the Wayback Machine, while tackling potential encoding and rate limit issues. 
- Identifying and downloading web media resources embedded in archived web pages, including common image formats, as well as multimedia content in historical formats, such as Flash, Shockwave, and VRML.   
- Technical limitations and ethical considerations in scraping the Wayback Machine and alternative approaches to using archived web data for quantitative and computational historical research. 


# Course structure

The rest of the lesson is roughly structured into two parts. In the first part, after we outline the learning outcomes and prerequisites, we will briefly review how the Wayback Machine works and introduce the Wayback Machine CDX Server API, which we can use to find all available archived snapshots of a given URL on the Wayback Machine. Next, we will showcase how to detect and scrape different types of media content in an archived web page, with a focus on legacy formats that you may encounter in web pages from the 1990s-early 2000s. 

The second part is the case study where we will use the tools and techniques we introduced in the first part to scrape the Wayback Machine for banner ads appearing on popular Japanese websites. We will discuss 


# Getting Started with Programmatic Access to the Wayback Machine

The earliest institutional attempts to preserve information available on the web started shortly after the web became the main medium for the presentation and transmission of information over the Internet around the mid-1990s. The ensuing years saw the emergence of a range of web archiving initiatives. In this tutorial, we will focus on scraping archived web content on the Wayback Machine. Founded in 1996, the Internet Archive’s Wayback Machine is the world’s first web archive, and today it holds billions of web pages from around the world dating back to 1996, publicly accessible through its website at [web.archive.org](http://web.archive.org). 

The Wayback Machine proactively archives the web, mainly by running a web crawler that follows and saves links on the web in a way not dissimilar to search engines. Given its founding date and the worldwide scope of its collection, the Wayback Machine is also the only place where some of the earliest web pages on the Internet may be found. 

You may already know how to access archived snapshots of a given historical URL on the Wayback Machine by entering the URL manually on the Wayback Machine’s home page and then choosing a particular archived snapshot of the URL to view on the Wayback Machine’s calendar interface. While the calendar interface is convenient for manual exploration of single URLs, it becomes impractical when you need to work with a set of URLs, when you want to retrieve multiple archived snapshots of one given URL, or when you need to scrape certain elements from a set of archived web pages. To handle these tasks, you will need a way to access the archive through code rather than through the web interface.

There are different ways to access archived web data on the Wayback Machine programmatically. In this tutorial, we are going to use the Wayback Machine’s CDX Server API to retrieve available archived copies of web resources at a given URL on the Wayback Machine. CDX, or crawl index records, is a metadata index generated during the crawling process describing web data archived by the Wayback Machine’s crawler. Aside from the CDX API, the Wayback Machine can also be queried through the [Memento Protocol API](https://ws-dl.blogspot.com/2013/07/2013-07-15-wayback-machine-upgrades.html) and the [Wayback Machine Availability API](https://archive.org/help/wayback_api.php). All three APIs are available free of charge, though the CDX Server API returns much more information about each archived snapshot of a given URL than the two other alternatives mentioned above, such as HTTP status codes and sizes of the snapshots. 

In addition to APIs, researchers may also be interested in accessing archived web data through integrated research toolkits and platforms such as the Internet Archive’s [Archives Research Compute Hub](https://archive-it.org/arch/). Researchers intending to use these toolkits and platforms generally need to have access to raw archived web data in WARC format or enter a partnership with an archiving organization such as the Internet Archive, but they can provide advanced features such as full-text search and data visualisation. If your research involves a large number of URLs that makes manually scraping impractical, using a research toolkit or platform might be a better choice. 


# Downloading archived web pages from the Wayback Machine

The tools and methods to scrape media resources off archived web pages on the Wayback Machine do not differ much technically from those commonly used to scrape the live web. However, to ensure that we can interpret scraped archived web data correctly, it is important to know how the Wayback Machine saves content on the web, and how it serves archived web content to the user on its web interface. 

# Understanding web archive replay and time skew

Web archive scholars have long emphasized that archived web content differs significantly from traditional archival materials, and archived web materials may not be identical to what was online in the past. Even on the live web, a particular resource on the web may be experienced differently by different groups of people due to variety of technical and non-technical factors. The dynamic nature of the web means that web archives are always incomplete. As Niels Brügger notes, an archived web page is "better understood as an actively created and subjective reconstruction" of what the original page may have looked like at a given point in time [^1]. The way an archived web page is *reconstructed* has implications for how we scrape, analyze, and interpret archived web content. 

A typical web page consists of a primary HTML document that defines its structure and textual content, along with numerous auxiliary resources such as images, stylesheets, scripts, and other media files. These resources are referenced in the HTML document by their own URLs. For example, an image in a web page is usually embedded using the `<img>` tag, with the image file’s location specified in the src attribute (e.g., `<img src="images/logo.gif">`). Similarly, stylesheets and scripts are linked using `<link>` and `<script>` tags. To display the page correctly, the browser must fetch all of these external resources in addition to the main HTML file. 

When the Wayback Machine archives a web page, it attempts to archive both the HTML and all linked resources. However, if the Wayback Machine served archived HTML files exactly as they were originally written, the browser would try to fetch all linked resources from their original locations on the live web. Because many of these resources no longer exist online, this would result in broken images, missing styles, or incomplete functionality. To address this, the Wayback Machine modifies the HTML source by rewriting each resource URL to point to its archived version. This ensures that pages load as completely as possible using content from the archive rather than the live web.

This process of dynamically assembling and serving an archived page by combining its HTML with available archived resources is called **replay**. During replay, the Wayback Machine retrieves the archived HTML file, rewrites URLs to point to corresponding resources in the archive, and presents the reconstructed page to the user. 

Ideally, all resources on a web page would all be archived at the same moment as the HTML file. In practice, however, technical limitations often prevent the archive from capturing every resource at once. As a result, the Wayback Machine makes a “best effort” replay by stitching together the HTML file with the closest available versions of its linked resources from other capture dates. In some cases, elements appearing in a reconstructed page may have been archived days, months, or even years apart. This temporal incoherence is sometimes referred to as *time skew* [^TIMESKEW]. For researchers intending to use archived web content as source materials, time skews can complicate efforts to interpret a page’s content or intended user experience as it originally appeared on the web.

In the case study section, we present a general workflow for scraping media from archived web pages on the Wayback Machine. This workflow is designed with these archival quirks in mind, helping researchers identify, retrieve, and interpret media resources while accounting for time skews. The lesson is specifically geared towards web pages from the late 1990s \- early 2000s. 

It is worth noting that aside from the Wayback Machine's own replay mechanisms, there are other factors that may influence how an archived web page appears to a user today, such as differences in browser rendering engines [^OLDWEB], changes in default fonts or screen resolutions, and missing support for obsolete media formats like Flash [^FLASHSUPPORT]. While researchers need to know about their existence, these factors do not directly concern scraping, as they affect how archived content is rendered in a browser rather than how it is stored or can be programmatically extracted from the archive. 


# Anatomy of an archived web page

To better understand how the Wayback Machine replays archived web content, let’s observe an archived snapshot of Google’s home page saved by the Wayback Machine in 1999, available at [https://web.archive.org/web/19990117032727/http://www.google.com/](https://web.archive.org/web/19990117032727/http://www.google.com/). 

We can begin by looking at the URL itself. Typically, the URL of an archived web resource on the Wayback Machine looks like this:

```
https://web.archive.org/web/[timestamp in yyyymmddhhmmss][optional request flag]/[original URL]
```

The timestamp in the URL is in Coordinated Universal Time (UTC). Therefore, this particular snapshot of Google’s home page was captured on January 17, 1999, 03:27:27 UTC. The timestamp is sometimes followed by an optional request flag, whose role we will explain shortly. 

Note that if you provide an incomplete timestamp, or a timestamp on which the Wayback Machine does not have an archived snapshot of the given URL, the Wayback Machine will automatically find and return the snapshot captured at the closest available timestamp to the one given. For example, if you visit [https://web.archive.org/web/**19990116**/http://www.google.com/](https://web.archive.org/web/19990116/http://www.google.com/), the Wayback Machine will automatically redirect you to the archived snapshot of [google.com](http://Google.com) captured at the closest available timestamp to 19990116, which is 19990117032727. 

Now, you can open the URL in your browser, and you will be greeted with an archived version of Google’s homepage in 1999.

{% include figure.html filename="google-screenshot-1.png" alt="A screenshot of a Wayback Machine capture of google.com made on January 17, 1999, 03:27:27 UTC" caption="Wayback Machine capture of google.com made on January 17, 1999" %}

The first thing you may notice on the page \- apart from how different Google looked back then \- is the existence of a toolbar on the top of the page. The toolbar allows you to quickly navigate between archived snapshots captured at different points in time. It also allows you to view timestamps of linked resources on the archived web page by clicking “About this capture” [^TOOLBAR], which should give you a sense of to what degree the page suffers from time skew. 

{% include figure.html filename="google-screenshot-about-capture.png" alt="A screenshot of a Wayback Machine capture of google.com made on January 17, 1999, 03:27:27 UTC, with the About This Capture toolbar section open" caption="Wayback Machine capture of google.com made on January 17, 1999, displaying About This Capture section" %}

In our case, we can see that the Google logo \- the only image file on the page \- is actually archived 3 months 17 days from the timestamp of the current snapshot. While this is technically a case of time skew, we can be sure that the logo should be identical to what may have been displayed on Google’s website on the date of the page snapshot by triangulating with other sources. 

Next, we can examine the source code of the archived web page using the inspector, which is a browser feature that allows us to view elements on the page and their corresponding sections in the HTML source code. On most browsers, you can press Ctrl+Shift+I (Windows/Linux) or Cmd+Option+I (Mac) to open the inspector. 

{% include figure.html filename="google-screenshot-inspect-element.png" alt="A screenshot of using the browser inspector tool to examine the Google logo, on a Wayback Machine capture of google.com made on January 17, 1999, 03:27:27 UTC" caption="Inspecting the Google logo on a Wayback Machine capture of google.com made on January 17, 1999" %}

We can see that all hyperlinks on the page have been rewritten with a prefix /web/19990117032727. This allows you to follow links on the web page and navigate to the closest available snapshot of the linked page, as if you were browsing the live web in 1999\. Also note that the `src` attribute of the `<img>` element representing the Google logo is "/web/19990117032727im\_/[http://www.google.com/google.jpg](http://www.google.com/google.jpg)". The “/web/19990117032727im\_/” part is added by the Wayback Machine. This means that when your browser is loading the web page, the Google logo image is not loaded from the original URL (“[http://www.google.com/google.jpg](http://www.google.com/google.jpg)”), but its archived version on the Wayback Machine \- the full URL of the archived logo image is [https://web.archive.org/web/19990117032727im\_/http://www.google.com/google.jpg](https://web.archive.org/web/19990117032727im_/http://www.google.com/google.jpg). If you open the image link URL directly in your web browser, you will see that the Wayback Machine automatically redirected the URL to [https://web.archive.org/web/19990504112211im\_/http://www.google.com/google.jpg](https://web.archive.org/web/19990504112211im_/http://www.google.com/google.jpg), which is the closest available archived copy of the image file that the Wayback Machine could find. The time difference between the timestamp in the new URL (19990504112211) and the timestamp in the URL before redirection (19990117032727) corresponds to the 3 month 17 days time difference reported on the Wayback Machine toolbar. We can therefore obtain information about the archival date of each individual resource on the page and assess the extent of time skew by comparing the timestamps of the reconstructed page and its component resources. 

Lastly, you may notice the rewritten image URL contains a request flag `im_`.  A request flag is a special modifier inserted between the timestamp and the original URL in a Wayback Machine link [^REQUESTFLAG]. It controls how the archived content is served during replay. In this particular case, the flag `im_` instructs the Wayback Machine to return the archived resource as-is without applying any kind of modifications, which allows the browser to load the image correctly in the archived web page. `im_` is also applied to media resources like audio and video files. Below is a list of other request flags that you may encounter in archived web pages: 

- `cs_` and `js_`: These flags are usually added to CSS and JavaScript files. Wayback Machine will rewrite any URLs in these files to their archived versions according to the timestamp provided, and add a note of archival capture information to the file. To retrieve CSS and JS files as they are originally archived, use the `id_` flag as described below.   
- `oe_`: Similar to `im_`, but is used for embedded objects like Flash, Shockwave, etc. 

Researchers scraping the Wayback Machine may find the following two flags useful in some scenarios: 

- `id_`: Adding this flag forces the Wayback Machine to return an archived web page as-is, without modifying any URLs in the document. This will cause many in-page resources to fail to load in a browser, but it allows researchers to analyze the original HTML exactly as it was archived \- useful for studying the structure, authoring practices, or embedded metadata of historical web pages without interference from replay modifications.  
- `if_`: Adding this flag removes the Wayback Machine toolbar from an archived web page, but the URLs of resources and hyperlinks will still be rewritten. Useful for capturing screenshots, or if you want to take advantage of the rewritten URLs during the scraping process. 


# Querying available archived snapshots of a given URL through the Wayback Machine CDX Server API

The Wayback Machine’s CDX Server API allows us to see all available archived snapshots of a given URL on the Wayback Machine, along with metadata of the snapshots that will be useful for us to curate a list of URLs to scrape. In other words, the CDX Server API provides us with the same information that we may access through the Wayback Machine’s calendar interface, but we will be able to process the information programmatically using a language like Python. 

Accessing the Wayback Machine’s CDX API is as simple as accessing any other REST APIs. The URL endpoint to access the API is: 
```
http://web.archive.org/cdx/search/cdx?url=[The URL you want to check available archived snapshots thereof]
```
Using Python’s requests library, we can make a simple request to query all available archived snapshots of a given URL. As an example, here are the results of all available archived snapshots of [lycos.co.jp](http://lycos.co.jp), the Japanese version of the Lycos, a web search engine popular in the 1990s and early 2000s: 

```python
import requests

# Target CDX API endpoint
cdx_url = "http://web.archive.org/cdx/search/cdx"
params = {
    "url": "lycos.co.jp"
}

# Make the GET request
response = requests.get(cdx_url, params=params)

# Check for a successful response
if response.status_code == 200:
    print(response.text)
else:
    print(f"Request failed with status code: {response.status_code}")
```

You may also access the results of this API request by visiting directly [http://web.archive.org/cdx/search/cdx?url=lycos.co.jp](http://web.archive.org/cdx/search/cdx?url=lycos.co.jp). The first entry of the results is reproduced below: 

```
jp,co,lycos)/ 19981212030704 http://www.lycos.co.jp:80/ text/html 200 6766K4GBJSIZJOGPUWSRF7S7EMWPA34N 4700
```

The data returned is in a tabular format with the columns separated by space. By default, the order of the columns is as follows: 

```
"urlkey","timestamp","original","mimetype","statuscode","digest","length"
```

A detailed explanation of the meanings of the columns is available [here](https://support.archive-it.org/hc/en-us/articles/115001790023-Access-Archive-It-s-Wayback-index-with-the-CDX-C-API), but the key columns here that we are going to use in our lesson are `timestamp`, `mimetype`, `statuscode`, and `digest`. 

The `timestamp` identifies the exact point in time at which the web resource was captured. The timestamp is provided in the format of `yyyymmddhhmmss` in UTC timezone, which is identical to the timestamp format appearing in Wayback Machine archived snapshot URLs. The line reproduced above therefore represents a snapshot taken of [lycos.co.jp](http://lycos.co.jp), on December 12, 1998 03:07:04 UTC time. You can access the archived snapshot of the URL on the Wayback Machine at [https://web.archive.org/web/19981212030704/lycos.co.jp](https://web.archive.org/web/19981212030704/lycos.co.jp) (the Wayback Machine can automatically complete the missing http:// in the URL)

The `mimetype` indicates the type of file or content that was captured. Mimetype is a technical standard for identifying the format of a file or data being transmitted over the internet.  A list of [common mimetypes can be found here](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/MIME_types/Common_types). 

The `statuscode` represents the HTTP response code received by Wayback Machine’s crawler when it saved the page from the live web. If a resource is technically archived successfully, the HTTP response code should be `200`. Other common HTTP response codes that you may encounter include `404` (indicating page/resource not found), `403` (access forbidden), and `301` (resource moved permanently). 

The `digest` is a content “fingerprint” generated by the Wayback Machine \- a cryptographic hash (SHA-1) of the archived resource’s raw bytes. The `digest` is used to detect when two snapshots contain identical content (even if captured at different times) and to ensure data integrity.

For popular websites, the Wayback Machine may have tens of thousands of snapshots taken from 1996 to today, which may make an API query take a long time to finish. Fortunately, the Wayback Machine CDX Server API allows us to filter the results by adding parameters to the query. For example, we can let the API return only snapshots of [lycos.co.jp](http://lycos.co.jp) taken between January 1, 2000 and December 31, 2000 with the HTTP status code 200: 

```
http://web.archive.org/cdx/search/cdx?url=lycos.co.jp&from=20000101&to=20001231&filter=statuscode:200
```

Our new API request returns only 70 results. In contrast, our original API request returns 2835 results. As a rule of thumb, always attempt to narrow your API request by applying server-side filters to limit the volume of data returned, and then you can further refine the data in Python. A detailed documentation of the Wayback Machine CDX API, including the available query options to help you filter results, is available [here](https://archive.org/developers/wayback-cdx-server.html). 

# Choosing a download method

Most of the tools for scraping live websites can be used to download archived pages from the Wayback Machine. In this tutorial, we will rely on Python’s requests library because it’s lightweight, easy to script, and handles basic HTTP fetches reliably. 

An inherent limitation of downloading the HTML data using requests or a download tool like wget is that any on-page client-side JavaScript content is not executed. Some web pages may use JavaScript to populate content or redirect users to another web page. If you find yourself needing to scrape historical web pages that involve heavy client-side scripting, consider using a browser automation framework such as Selenium or Puppeter. These tools can help you launch a real browser to download the web pages, and they are able to execute scripts and let you interact with the page and select particular page elements for scraping. However, these tools generally demand more system resources, and you need to check whether replaying archived scripts might alter the integrity or authenticity of the content you are examining. 

# Dealing with legacy encoding for non-English web pages

You may encounter web page encoding issues when you are scraping non-English web pages made in the 1990s and early 2000s. Encoding refers to the mechanism by which textual data is represented on computers. Early web pages often used a variety of region-specific encoding standards (e.g., Shift-JIS for Japanese, EUC-KR for Korean, GB2312 for Simplified Chinese). These encoding standards are now largely superseded by UTF-8, a standard that can represent characters from many languages around the world. However, when dealing with non-English web pages from the late 1990s and early 2000s, it is still often necessary to specify page encoding so that the content could be processed correctly. 

If you are using requests to download archived web pages, you may use the library’s encoding detection mechanism to detect page encoding and ensure that non-English content is processed correctly. In the following example, we use `requests` to download a December 1996 archived copy of the home page of Ming Pao, a major Chinese-language newspaper in Hong Kong to demonstrate how to use the encoding detection mechanism of `requests` to rectify encoding errors: 

```python
import requests

# Archived URL of Ming Pao from December 1996  
url = "https://web.archive.org/web/19961220194056/http://www.mingpao.com/newspaper/"

# Make the request  
response = requests.get(url)

# Attempt 1: Without setting encoding (will likely print gibberish)  
print(response.text[:400])  # print first 400 characters

## While the HTML tags will still show up correctly, the actual text will show up as gibberish, like this:
##  <CENTER><H2>¤@¤E¤E¤»¦~ ¤Q¤G¤ë¤G¤Q¤é ¬P´Á¤­</H2></CENTER> 

# Attempt 2: With detected encoding using apparent_encoding  
response.encoding = response.apparent_encoding  
print(response.text[:400])  

## The Chinese text in the HTML should show up here correctly, like this: 
## <CENTER><H2>一九九六年 十二月二十日 星期五</H2></CENTER>  
```
	  
If you are using browser automation software like Selenium to download web pages, it is unlikely that you will need to handle encoding manually, as modern browsers generally are good at detecting encoding of web pages (including web pages produced in the 1990s and early 2000s). 

# Avoiding Wayback Machine rate limiting

Like many public web services, the Wayback Machine employs rate limiting to prevent server overload from excessive requests. The Wayback Machine currently does not make its thresholds for rate limiting public, though there are [user reports](https://github.com/edgi-govdata-archiving/wayback/issues/137#issuecomment-1845803523) citing conversations with Internet Archive employees confirming the existence of rate limiting thresholds. When you exceeded rate limits, the Wayback Machine may temporarily block your IP address or return HTTP error codes like 429 (Too Many Requests) or 503 (Service Temporarily Unavailable). 

To handle these limitations, we can implement an [exponential backoff](https://en.wikipedia.org/wiki/Exponential_backoff) retry strategy using Python's `⁠tenacity` library. This approach automatically retries failed requests with progressively longer delays between attempts:

```python
from tenacity import retry, stop_after_attempt, wait_exponential
import requests

@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=8))
def download_wayback_page(url):
    response = requests.get(url)
    response.raise_for_status()  # Raises an exception for HTTP error codes
    return response
```

The exponential backoff strategy works by waiting longer between each retry attempt (starting at 2 seconds, then doubling up to a maximum of 8 seconds). This gives the server time to recover while ensuring temporary connection issues will not cause your script to fail immediately. You may adjust these parameters according to your network conditions as necessary. 


# **Identifying embedded media on archived web pages**

In this section, we will give a brief overview of how common types of web media are referenced in HTML, with specific attention to historical media formats that you may encounter on archived web pages from the late 1990s and early 2000s. 

### Images

Images are inserted into a web page with the `<img>` tag, with the path to the image recorded in the `src` attribute of the `<img>` element. Many images also come with an `alt` attribute, which provides a textual description of the image. The `alt` text is usually displayed when the image cannot be loaded, or if the user is using a screen reader. For researchers today, the `alt` tag might be helpful to identify the intended content or function of an image when the original file is missing or when conducting textual analysis of archived pages.

In web pages from the 1990s and early 2000s, it was also a common practice to specify image height and width using height and width attributes in the \<img\> element. This allows browsers to finish rendering the layout of the web page even when the image is not fully loaded or if it fails to load. Researchers today may use the provided width and height information to find images fitting specific dimensions. 

As mentioned above, by default the Wayback Machine rewrites image URLs with the `im_` request flag. You should append the same flag when scraping the image files to ensure that you get the original image files. 

### Sound and video

On web pages authored in the 2010s and later, sound files and video files are usually embedded using the \<audio\> and \<video\> tags. A typical \<audio\> tag may look like this (\<video\> tags follow essentially the same convention): 

```html
<audio controls>
    <source src="music.ogg" type="audio/ogg">
    <source src="music.mp3" type="audio/mpeg">
    Your browser does not support the audio element.
</audio>
```

You should be able to download sound and video files by scraping the `src` attribute of the `<source>` tags. By default, the Wayback Machine also rewrites sound and video URLs with the `im_` flag, and you should append the same flag when scraping these files. 

Some web pages may employ custom media players, which may make the media files less likely to be archived. In older web pages, sound and video files may be embedded using `<embed>` or `<object>` tags, which we will cover in the next section. 

### Legacy media: \<embed\> and \<object\>

`<embed>` and `<object>` are two HTML tags commonly used to add non-image media resources on web pages  in the 1990s and early 2000s. During the browser wars of the late 1990s, `<embed>` was preferred by Netscape while Internet Explorer pushed the `<object>` element as a container for web media content. As a result, many early webpages included both tags (often nested) to ensure their media would play correctly in whichever browser the visitor used [^BROWSERWAR]. 

Fortunately, you will be able to find out the path to the content linked using information contained in either tag. The following example is taken from a [real-life web page from 2004](https://web.archive.org/web/20040625234530/http://www.poly.edu:80/huss/idm/idmi.html) featuring Shockwave content:     

```html
<object classid="clsid:166B1BCA-3F9C-11CF-8075-444553540000" codebase="http://download.macromedia.com/pub/shockwave/cabs/director/sw.cab#version=8,5,0,0" width="800" height="600">
    <param name="src" value="idmi.dcr">
    <param name="swStretchStyle" value="fill">
    <param name="AutoStart" value="true">
    <embed src="idmi.dcr" width="800" height="600" autostart="true" pluginspage="http://www.macromedia.com/shockwave/download/">
</object>
```

In this example, the embedded Shockwave movie file is `idmi.dcr`, which is seen in both the `src` attribute on the \<embed\> tag or the corresponding \<param\> tag under the parent \<object\> tag. By default, the Wayback Machine will rewrite URLs of embedded media files with the `oe_` request flag. When downloading these files, you should append the same flag. 

In most cases, types of different embedded media files can be distinguished by their file extension. A list of legacy media formats commonly seen in web pages from the late 1990s \- early 2000s is provided below: 

| Format | File extension |
| :---- | :---- |
| QuickTime | mov |
| RealMedia | ra, rm, ram, rmvb |
| Macromedia Director (Shockwave) | dcr |
| Macromedia Flash | swf |
| VRML | wrl, wrz |


### Frames

In the late 1990s and early 2000s, the HTML frame was a popular yet controversial method used by some web developers to build complicated page layouts, such as independently scrollable navigation sections. The HTML structure of a web page containing frames may look like this:


# Further readings

For web archives in historical research, see For a history of web archiving, see Ian Milligan's [Averting the Digital Dark Age: How Archivists, Librarians, and Technologists Built the Web a Memory](https://www.press.jhu.edu/books/title/53671/averting-digital-dark-age).  

The Environmental Data and Governance Initiative (EDGI) produces a Python library aptly named `wayback` that packages a number of Wayback Machine CDX Server API features into Python functions that can be readily imported into your project. Refer to [https://github.com/edgi-govdata-archiving/wayback](https://github.com/edgi-govdata-archiving/wayback) for more information. 

HTML reference books published in the late 1990s and early 2000s are incredibly helpful for today’s researchers to understand web authoring practices prevalent in that era that are today largely forgotten. Some of the books are now available to borrow on the Internet Archive:
 
 - [HTML Pocket Reference, Second Edition](https://archive.org/details/htmlpocketrefere00nied), written by Jennifer Niederst. Published by O'Reilly and Associates. 
 - [HTML: The Complete Reference, Third Edition](https://archive.org/details/htmlcompleterefe00powe_0/mode/2up), written by Thomas A. Powell. Published by Osborne/McGraw-Hill. 
 - [HTML, Java, CGI, VRML, SGML Web Publishing Unleashed]()

 



# References
[^1]: Brügger, Niels. “Web History and Social Media.” In The SAGE Handbook of Social Media, edited by Jean Burgess, Alice Marwick, and Thomas Poell. 1 Oliver’s Yard, 55 City Road London EC1Y 1SP: SAGE Publications Ltd, 2018. https://doi.org/10.4135/9781473984066.

[^EDGI-WAYBACK]: “Edgi-Govdata-Archiving/Wayback.” Python. 2019. Reprint, Environmental Data and Governance Initiative, June 11, 2025. https://github.com/edgi-govdata-archiving/wayback.

[^BROWSERWAR]: Castro, Elizabeth. “Chapter 17: Multimedia.” In HTML for the World Wide Web, 293–312. Peachpit Press, 2003.

[^TOOLBAR]: Graham, Mark. “Wayback Machine Playback… Now with Timestamps!” Internet Archive Blogs (blog), October 5, 2017. https://blog.archive.org/2017/10/05/wayback-machine-playback-now-with-timestamps/.

[^TIMESKEW]: Ankerson, Megan Sapnar. “Read/Write the Digital Archive: Strategies for Historical Web Research.” In Digital Research Confidential, edited by Eszter Hargittai and Christian Sandvig, 29–54. The MIT Press, 2015. https://doi.org/10.7551/mitpress/9386.003.0004.

[^REQUESTFLAG]: There appears to be no consensus on the name of this component in archived snapshot URLs on the Wayback Machine. In this lesson, we call them "request flags," which is taken from the [release notes](https://web.archive.org/web/20231221054022/https://archive-access.sourceforge.net/projects/wayback/release_notes.html) of the Wayback Machine software developed by the Internet Archive. 
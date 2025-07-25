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

As historians increasingly turn their attention to the 1990s and early 2000s - a period marked by rapid expansion and mainstream adoption of the web - the value of web archives as historical sources is gaining wider recognition.  While many web archives like the Wayback Machine provide a user-friendly interface for looking up archived web content by URL, researchers looking to perform computational or quantitative analysis may prefer accessing archived web content programmatically in order to examine the archival availability of historical URLs, bulk download archived web pages, and extract specific page elements for further analysis. 

In this lesson, we will use the Wayback Machine’s CDX Server API to scrape media resources featured on archived web pages on the Wayback Machine. Specifically, we are going to build a small dataset of historical web banner ads appearing on popular Japanese-language websites in the year 2000. The workflow introduced in the lesson is generally comparable to standard web scraping procedures, but we will cover a number of challenges specific to scraping historical web pages archived on the Wayback Machine - especially non-English web pages from the 1990s and early 2000s. 


## Prerequisites

This lesson is designed for people who have an intermediate understanding of Python and HTML. You should have prior experience with web scraping in Python and BeautifulSoup, as well as a basic understanding of how web archives work, though we are going to cover some of the background information in the next section. 

If you are new to Python and HTML, you may want to consult Programming Historian lessons on [Python](https://programminghistorian.org/en/lessons/introduction-and-installation) and [HTML](https://programminghistorian.org/en/lessons/viewing-html-files), and subsequent lessons in that series. You may also want to check out the lessons [Creating APIs with Python and Flask](https://programminghistorian.org/en/lessons/creating-apis-with-python-and-flask) and [Introduction to Populating a Website with API Data ](https://programminghistorian.org/en/lessons/introduction-to-populating-a-website-with-api-data) to familiarize yourself with basic concepts related to application programming interfaces (APIs). 

You can follow the lesson on any mainstream operating system you prefer, including Windows, macOS, and popular Linux distributions, as long as you can get a relatively recent version of Python installed on your operating system. At the time of writing, the most recent Python version is 3.13. On Python, you will need to have the following libraries installed: 

- requests 
- BeautifulSoup  
- pillow  
- tenacity 

We recommend that you install [Anaconda](https://anaconda.org/), a distribution of Python specifically designed for data science research for this lesson. A standard installation of Anaconda includes the first three libraries, and you can easily install tenacity by running `pip install tenacity`. 

## Learning outcomes

By the end of this lesson, you will learn: 

- Using the Wayback Machine CDX Server API to check the archival availability of web content located at a given historical URL.    
- Batch downloading archived web pages from the Wayback Machine, while tackling potential encoding and rate limit issues. 
- Identifying and downloading web media resources embedded in archived web pages, including common image formats, as well as multimedia content in historical formats, such as Flash and Shockwave. 
- Technical limitations and ethical considerations in scraping the Wayback Machine. 


## Course structure

The rest of the lesson is roughly structured into two parts. In the first part, we will briefly review how the Wayback Machine works, its limitations, and introduce the Wayback Machine CDX Server API, which allows us to access archived content on the Wayback Machine programmatically. Next, we will showcase how to detect and scrape different types of media content on an archived web page, with a focus on legacy formats that you may encounter in web pages from the 1990s-early 2000s. 

The second part is a case study where we will use the tools and techniques we introduced in the first part to scrape the Wayback Machine for banner ads appearing on popular Japanese websites in the month of May 2000. We will look at how such a dataset can TKTKTKTK


# Getting started with programmatic access to the Wayback Machine

There are different ways to access archived web content on the Wayback Machine programmatically. In this tutorial, we are going to use the Wayback Machine’s CDX Server API to retrieve available archived copies of web resources at a given URL on the Wayback Machine. Aside from the CDX Server API, the Wayback Machine can also be queried through the [Memento Protocol API](https://ws-dl.blogspot.com/2013/07/2013-07-15-wayback-machine-upgrades.html) and the [Wayback Machine Availability API](https://archive.org/help/wayback_api.php). All three APIs are available free of charge, though the CDX Server API provides much more information about archived web content than the other two APIs, such as sizes of the archived files and their HTTP response codes, which we will use in our scraping. 

In addition to APIs, researchers may also be interested in accessing archived web content through integrated research platforms such as the Internet Archive’s [Archives Research Compute Hub](https://archive-it.org/arch/) [^ARCH]. Researchers intending to use these platforms generally need to have access to raw archived web content in WARC format or enter a partnership with an archiving organization such as the Internet Archive, but they can provide advanced features such as full-text search and data visualization. If your research involves a large number of URLs that makes manually scraping impractical, using a research toolkit or platform might be a better choice. 


## Before you scrape: understanding how the Wayback Machine works and its limits

### How the web is archived

The earliest institutional attempts to preserve information available on the web started shortly after the web became the main medium for the presentation and transmission of information over the Internet around the mid-1990s. The ensuing years saw the emergence of a range of web archiving initiatives. Founded in 1996, the Internet Archive’s Wayback Machine is the world’s first web archive, and today it holds billions of web pages from around the world, publicly accessible through its website at [web.archive.org](http://web.archive.org) [^WAYBACK-MACHINE-NAME]. Given its founding date and the worldwide scope of its collection, the Wayback Machine is also the only place where some of the earliest web pages on the Internet may be found. 

The Wayback Machine proactively archives the web by running a web crawler, which is a program that systematically browses and downloads content on the web to be archived. When the Wayback Machine archives a web page, it attempts to archive both the HTML and its linked resources. We often use the verb capture to refer to the act of saving web content for inclusion in the archive. Any web content - be it a web page, a photo, an audio clip, or even a software installer in a zip file - that is captured at a particular point in time is commonly referred to as an archived snapshot.  

### Limitations of web archives

Web archive scholars have long emphasized that web archives differs significantly from traditional archives, and archived web content may not be identical to what existed online in the past. As web archive scholar Niels Brügger writes, an archived web page is "better understood as an actively created and subjective reconstruction" of what the original page may have looked like at a given point in time [^1]. While we are not going to dive deep into the technical details of web archiving, you should be aware of the following four factors leading to this discrepancy: 

First, any web archive can only capture content that is publicly accessible on the web. Any web content requiring authentication - for example, web pages on company intranets and learning management systems requiring user login - cannot be archived by an web crawler. Web archives also cannot capture server-side programs, which means while you can access a snapshot of google.com taken in 1998 to observe its user interface, you cannot use the archived snapshot of google.com to search the 1998 web. 

Second, the web is a dynamic medium, and content that is served from a single URL may appear and behave differently to different users based on many contextual factors, including the user’s browser, device, software settings, location, and even local laws and regulations. A user visiting youtube.com from Seoul using a mobile phone and a user visiting youtube.com from Singapore using a desktop computer will be greeted with two very different web pages. When a web archive archives a web page, it typically captures only what was served to the crawler at that particular time, from a particular location, using a particular set of hardware, software, and network configuration. As a result, an archived snapshot of a URL may not reflect how content available at that URL may have appeared to different groups of users when it was available on the live web. 

Third, hardware and software today may differ significantly from those available when many archived web pages were originally created. A web page from the 1990s designed to be displayed on 15-inch monitors at 800 * 600 resolution may not be rendered correctly on an 32-inch ultrawide monitor made in 2024. Similarly, a modern web browser may not be able to display Flash animations that were popular in the 2000s. There are recent efforts such as oldweb.today [^OLDWEB] and Ruffle [^FLASHSUPPORT] that seek to address this issue through emulating old web browsers and implementing the capability to playback legacy media formats in today's browsers.

The fourth factor, and arguably the most important factor that you should be aware of for scraping media files appearing on archived web pages and using them as historical sources, is that archived web pages as they appear on web archives like the Wayback Machine are often not *temporally coherent*. For example, below is a screenshot of Wayback Machine's [archived snapshot](https://web.archive.org/web/19990202064014/http://hudir.hungary.com/) from February 2, 1999 of HuDir, an English-language web directory of Hungary-related links. The page features a banner ad that advertises an event to be held in November 2004 - which is certainly unusual for a web page ostensibly from 1999. This is a case of what some scholars call temporal violation or time skew. 

{% include figure.html filename="hudir.png" alt="A screenshot of hudir.hungary.com in 1999 displaying a banner ad promoting an event in 2004" caption="A screenshot of hudir.hungary.com in 1999 displaying a banner ad promoting an event in 2004" %}

Time skew occurs on the Wayback Machine because the web crawler program cannot always capture every element of a web page at the exact same moment. As a result, when the user requests an archived snapshot of a web page on the Wayback Machine's web interface, the Wayback Machine delivers a "best effort" reconstruction of how an archived web page may look and behave in the past: it modifies URLs of linked resources on the archived page so that they may be loaded from the closest available versions in the archive, even if those versions were captured on different dates than the HTML document itself. The resulting page may resemble the past appearance and functionalities of the original web page. However, it also means that parts of the page may come from different moments in time - sometimes months or even years apart from each other - which can result in misleading combinations of content that never actually appeared together. 

The Wayback Machine allows us to see the capture dates of linked resources on an archived web page by clicking “About this capture” on the toolbar [^TOOLBAR]. The toolbar appears by default when you load an archived snapshot from its calendar interface. In the above example, the banner ad image was captured in November 2004 - 5 years and 10 months after the capture date of the web page - and it is not even the most time skewed element on the web page, with two GIF images on the page captured 17 years after the web page's capture date. 

{% include figure.html filename="hudir-skew.png" alt="A screenshot of the Wayback Machine toolbar showcasing time skew" caption="A screenshot of the Wayback Machine toolbar showcasing time skew" %}

For researchers, time skews can complicate the work of interpreting an archived web page, and raises important questions about what exactly an archived web page represents. When we scrape media resources on archived web pages on the Wayback Machine, we need to pay attention to whether - and to what extent - the resources we are scraping suffer from time skew. In the next section, we will demonstrate how Wayback Machine serves archived web pages, and how to detect time skews of page elements programmatically. 

## Anatomy of an archived web page on the Wayback Machine

To better understand how the Wayback Machine serves archived web content, let’s observe an archived snapshot of Google’s home page saved by the Wayback Machine in 1999, available at [https://web.archive.org/web/19990117032727/http://www.google.com/](https://web.archive.org/web/19990117032727/http://www.google.com/). Click the link, and you should be able to see an archived snapshot of Google's homepage. 

We can begin by looking at the URL itself. Typically, the URL of an archived web resource on the Wayback Machine looks like this:

```
https://web.archive.org/web/[timestamp in yyyymmddhhmmss][optional request flag]/[original URL]
```

The timestamp in the URL of an archived snapshot of any web object on the Wayback Machine - be it an HTML page, an image, or a zip file - is in Coordinated Universal Time (UTC). Judging from its timestamp, this particular snapshot of Google’s home page was captured on January 17, 1999, 03:27:27 UTC. The timestamp is sometimes followed by an optional request flag, whose role we will explain shortly. 

If you provide an incomplete timestamp, or a timestamp on which the Wayback Machine does not have an archived snapshot of the given URL, the Wayback Machine will automatically redirect you to the snapshot captured at the closest available timestamp to the requested timestamp. For example, if you visit [https://web.archive.org/web/**19990116120000**/http://www.google.com/](https://web.archive.org/web/19990116120000/http://www.google.com/), the Wayback Machine will automatically redirect you to the archived snapshot of google.com captured at the closest available timestamp to 19990116, which is 19990117032727. 

Next, we can examine the source code of this archived web page snapshot using the inspector, which is a browser feature that allows us to view elements on the page and their corresponding sections in the HTML source code. On most browsers, you can press Ctrl+Shift+I (Windows/Linux) or Cmd+Option+I (Mac) to open the inspector. 

{% include figure.html filename="google-screenshot-inspect-element.png" alt="A screenshot of using the browser inspector tool to examine the Google logo, on a Wayback Machine capture of google.com made on January 17, 1999, 03:27:27 UTC" caption="Inspecting the Google logo on a Wayback Machine capture of google.com made on January 17, 1999" %}

We can see that the Wayback Machine has rewritten all hyperlinks on the page with a prefix `/web/19990117032727`. This technically allows you to follow links on the web page and navigate to the closest available snapshot of the linked page, as if you were browsing the live web in 1999, but you may also encounter cases where clicking a link on an archived page takes you years into the future or the past, due to a lack of archived snapshots taken close to your origin point in time. 

Also note that the `src` attribute of the `<img>` element representing the Google logo is "/web/19990117032727im\_/[http://www.google.com/google.jpg](http://www.google.com/google.jpg)". The “/web/19990117032727im\_/” part is added by the Wayback Machine. This means that when your browser is loading the web page, the Google logo image is not loaded from the original URL (“[http://www.google.com/google.jpg](http://www.google.com/google.jpg)”), but its archived version on the Wayback Machine \- the full URL of the archived logo image is [https://web.archive.org/web/19990117032727im\_/http://www.google.com/google.jpg](https://web.archive.org/web/19990117032727im_/http://www.google.com/google.jpg). 

If you open the archived logo image URL directly in your web browser, you will see that the Wayback Machine automatically redirected the URL to [https://web.archive.org/web/19990504112211im\_/http://www.google.com/google.jpg](https://web.archive.org/web/19990504112211im_/http://www.google.com/google.jpg), which is the closest available archived copy of the image file that the Wayback Machine could find. The time difference between the timestamp in the new URL (19990504112211) and the timestamp in the URL before redirection (19990117032727) corresponds to the 3 month 17 days time difference reported on the Wayback Machine toolbar. We can therefore obtain information about the archival date of each individual resource on the page and assess the extent of time skew by comparing the timestamps before and after redirection, which we will do using Python in our case study. 

Lastly, you may notice the rewritten image URL contains a request flag `im_`.  A request flag is a special modifier inserted between the timestamp and the original URL in a Wayback Machine link. It controls how the archived content is served from the Wayback Machine servers [^REQUESTFLAG]. In this particular case, the flag `im_` instructs the Wayback Machine to return the archived resource as-is without applying any modification, which allows the browser to load the image as an embedded image in the archived web page. `im_` is also applied to media resources, like audio and video files. Below is a list of other request flags that you may encounter in archived web pages: 

- `cs_` and `js_`: These flags are usually added to CSS and JavaScript files by the Wayback Machine when serving an archived web page. These flags tell the Wayback Machine to rewrite any URLs in these files to point to their archived versions according to the timestamp provided, and add a note of archival capture information to the file. To retrieve CSS and JS files as they are originally archived, use the `id_` flag as described below.   
- `oe_`: Similar to `im_`, but is used for embedded objects like Flash, Shockwave, VRML, etc. 
- `id_`: This flag instructs the Wayback Machine to return an archived web page without modifying any URLs in the document. This will cause many in-page resources to fail to load in a browser, but it allows researchers to analyze the original HTML exactly as it was archived. 
- `if_` and `_fw`: Both flags remove the Wayback Machine toolbar from an archived web page, but the URLs of resources and hyperlinks will still be rewritten. Useful for capturing screenshots, or if you want to take advantage of the rewritten URLs during the scraping process. These flags are originally designed to be used by the Wayback Machine when replaying archived web content involving `<iframe>` and `<frame>` elements, which we will cover later in the lesson. 


## Using the Wayback Machine CDX Server API

The Wayback Machine’s CDX Server API allows us to see all available archived snapshots of a given URL on the Wayback Machine, along with metadata of these snapshots. In other words, the CDX Server API provides us with the same information that we may access through the Wayback Machine’s calendar interface, but we will be able to process the information programmatically using a language like Python. The API supports all types of archived web files, not just web pages. 

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

## Choosing a download method

Most of the tools for scraping live websites can be used to download archived pages from the Wayback Machine. In this lesson, we will rely on Python’s requests library because it’s lightweight, easy to script, and handles basic HTTP fetches reliably. 

An inherent limitation of downloading the HTML data using requests or a download tool like wget is that any on-page client-side JavaScript is not executed. Some web pages may use JavaScript to populate content or redirect users to another web page. If you find yourself needing to scrape historical web pages that involve client-side scripting, consider using a browser automation framework such as [Selenium](https://www.selenium.dev/) or [Puppeteer](https://pptr.dev/). However, these tools generally demand more system resources, and you need to check whether executing archived scripts might alter the integrity or authenticity of the content you are examining. 

## Downloading from the Wayback Machine while detecting time skew

In the following example, we present a simple Python function that uses the requests library to download content from the Wayback Machine while detecting potential time skew. 

```python
from datetime import datetime # used to calculate time difference
import requests

def download_wm_snapshot(snapshot_url, file_name): 
    # TODO CODE HERE

```

## Dealing with legacy encoding for non-English web pages

You may encounter web page encoding issues when you are scraping non-English web pages made in the 1990s and early 2000s. Encoding refers to the mechanism by which textual data is represented on computers. Early web pages often used a variety of region-specific encoding standards (e.g., Shift-JIS for Japanese, EUC-KR for Korean, GB2312 for Simplified Chinese). These encoding standards are now largely superseded by UTF-8, a standard that can represent characters from many languages around the world. However, when dealing with non-English web pages from the late 1990s and early 2000s, it is still often necessary to specify page encoding so that the content could be processed correctly. 

If you are using requests to download archived web pages, you may use the library’s encoding detection mechanism to detect page encoding and ensure that non-English content is processed correctly. In the following example, we use `requests` to download a December 1996 archived copy of the home page of Ming Pao, a major Chinese-language newspaper in Hong Kong to demonstrate how to use the encoding detection mechanism of `requests` to rectify encoding errors: 

```python
import requests

# Archived URL of Ming Pao from December 1996  
url = "https://web.archive.org/web/19961220194056/http://www.mingpao.com/newspaper/"

# Make the request  
response = requests.get(url)

# Attempt 1: Without setting encoding (will likely print gibberish)  
print(response.text[:400])  ## Prints gibberish: <CENTER><H2>¤@¤E¤E¤»¦~ ¤Q¤G¤ë¤G¤Q¤é ¬P´Á¤­</H2></CENTER> 

# Attempt 2: With detected encoding using apparent_encoding  
response.encoding = response.apparent_encoding  
print(response.text[:400])  ## The Chinese text in the HTML should show up here correctly, like this:  <CENTER><H2>一九九六年 十二月二十日 星期五</H2></CENTER>  
```
	  
If you are using browser automation software like Selenium to download web pages, it is unlikely that you will need to handle encoding manually, as modern browsers generally are good at detecting encoding of web pages (including web pages produced in the 1990s and early 2000s). 

## Dealing with frames

In the late 1990s and early 2000s, the `<frame>` element was a popular yet controversial method used by some web developers to build complex page layouts. 

In lieu of a `<body>` element under the `<head>` element, a `<frame>`-based web page consists of a parent `<frameset>` element that defines how the browser window is divided into separate `<frame>`s. Each `<frame>` then loads its own HTML document. While this approach allowed for modular design, it also introduced accessibility, usability, and archival challenges. 

The example below is taken from a [2000 snapshot](https://web.archive.org/web/20000620031256/http://www.zooregon.org/) of the website of the Oregon Zoo in the United States. This web page is divided into two frames: a frame for displaying the navigation section on the left, and a content frame on the right. 

Load the URL in your browser and open the inspector, and the first thing that you may notice is that the archived web page is encapsulated in an `<iframe>` element with its `id` as `playback`. If you append the `if_` or `id_` flag to the timestamp, you will be able to access the archived web page without the `<iframe>` encapsulation. Part of the archived HTML file is reproduced below: 

```html
<head>...</head>
<frameset>
    <noframes>
	    <body>This site requires Netscape 3.0 or IE 3.0 or higher.</body>
    </noframes>
	<frame noresize="" src="/web/20000620031256fw_/http://www.zooregon.org/menuframe.htm" name="menuframe" scrolling="no" data-ruffle-polyfilled="">
	<frame noresize="" src="/web/20000620031256fw_/http://www.zooregon.org/bodyframe.htm" name="bodyframe" scrolling="auto" data-ruffle-polyfilled="">
</frameset>
```

As you may see, each `<frame>` has its own `src` attribute that has the URL of the embedded HTML document, with an `fw_` request flag. While you can see the HTML code of the web page embedded in each frame in the inspector window, you will need to fetch the embedded HTML pages separately if you download the main web page using requests. 

This also raises a challenge, as you need to figure out when the document in each frame was archived, and in turn when the resources in each embedded document was archived, in order to assess whether the main web page itself and its frames (and, possibly, frames inside them) suffer from time skew. In the following example, we use a Python function to process TKTKTK


## Dealing with Wayback Machine rate limiting

Like many public web services, the Wayback Machine employs rate limiting to prevent server overload from excessive requests. When you exceed rate limits, the Wayback Machine may return an HTTP 429 (Too Many Requests) error. 

The Wayback Machine currently does not make its thresholds for rate limiting public, though there is a [Github post](https://github.com/edgi-govdata-archiving/wayback/issues/137#issuecomment-1845803523) citing conversations with Internet Archive employees confirming the existence of rate limiting for both the CDX Server API and the web archive. According to the post, the recommended max number of requests for the CDX Server API and the web archive is as follows: 

 - `/cdx/*`: 48/min
 - `/web/NNNNNNNN*/*:` 480/min

In the case study, we will use the `time.sleep` function to observe these limits. However, in case we still hit 429 errors,  we can implement an [exponential backoff](https://en.wikipedia.org/wiki/Exponential_backoff) retry strategy using Python's `⁠tenacity` library. This approach automatically retries failed requests with progressively longer delays between attempts:

```python
from tenacity import retry, stop_after_attempt, wait_exponential
import requests

@retry(stop=stop_after_attempt(10), wait=wait_exponential(multiplier=1, min=2, max=32))
def download_wayback_page(url):
    response = requests.get(url)
    response.raise_for_status()  # Raises an exception for HTTP error codes
    return response
```

In the example code above, the tenacity library works by waiting longer between each retry attempt (starting at 2 seconds, then doubling up to a maximum of 32 seconds). This gives the server time to recover while ensuring temporary connection issues will not cause your script to fail immediately. You may adjust these parameters according to your network conditions as necessary. 


## Identifying embedded media on archived web pages

In this section, we will give a brief overview of how common types of web media are referenced in HTML, with specific attention to to historical media formats and HTML authoring practices that you may encounter on archived web pages from the late 1990s and early 2000s. 

### Images

Images are inserted into a web page with the `<img>` tag, with the path to the image recorded in the `src` attribute of the `<img>` element. Many images also come with an `alt` attribute, which provides a textual description of the image usually known as alt text. The alt text is usually displayed when the image cannot be loaded, or if the user is using a screen reader. For researchers today, the alt text might be helpful to identify the intended content or function of an image when the original file is missing or when conducting textual analysis of archived pages.

In web pages from the 1990s and early 2000s, it was also a common practice to specify image height and width using `height` and `width` attributes in the `<img>` element. This allows browsers to finish rendering the layout of the web page even when the image is not fully loaded or if it fails to load. Researchers today may use the provided width and height information to find images fitting specific dimensions, which we will demonstrate in our case study.  

As mentioned above, by default the Wayback Machine rewrites image URLs with the `im_` request flag. You should append the same flag when scraping the image files to ensure that you get the original image files. 

### Sound and video

On web pages authored in the 2010s and later, sound files and video files are usually embedded using the `<audio>` and `<video>` tags, and the syntax of both tags are very similar. The following example HTML snippet is taken from an [archived snapshot](https://web.archive.org/web/20150411044752/https://www.wework.com/) of the home page of the co-working office space company WeWork from 2014, which contains a video background:

```html
<video autoplay="autoplay" id="myvideo" loop="loop" muted="muted" src="//web.archive.org/web/20150411044752im_/https://da6bhbkkgqxyz.cloudfront.net/production/assets/welcome/wework_members-video_background_small-92daabed06e4e3aafdede211d9070544.mp4"></video>
```

As you can see, the URL to the file is present in the `src` attribute of the `<video>` element, and you may use the same method to locate paths to audio files in `<audio>` elements as well. 

Sometimes, instead of specifying URL to the media file in the `src` attribute, `<video>` and `<audio>` elements will contain multiple `<source>` elements that specify alternative media files in different formats. The URLs to these files are located in the `src` attribute of these elements. 

By default, the Wayback Machine also rewrites sound and video URLs with the `im_` flag, and you should append the same flag when scraping these files. 

### Media in \<embed\> and \<object\>

`<embed>` and `<object>` are two HTML tags commonly used to add non-image media resources on web pages  in the 1990s and early 2000s. During the browser wars of the late 1990s, `<embed>` was preferred by Netscape while Internet Explorer pushed the `<object>` element as a container for web media content. As a result, many early webpages included both tags (often nested) to ensure their media would play correctly in whichever browser the visitor used [^BROWSERWAR]. 

Fortunately, you will be able to find out the path to the content linked using information contained in either tag. The following is a real-life example, taken from an archived snapshot of the website of the [Integrated Digital Media Program]((https://web.archive.org/web/20040625234530/http://www.poly.edu:80/huss/idm/idmi.html)) of NYU's Tandon School of Engineering, featuring Shockwave content:

```html
<object classid="clsid:166B1BCA-3F9C-11CF-8075-444553540000" codebase="https://web.archive.org/web/20040625234530oe_/http://download.macromedia.com/pub/shockwave/cabs/director/sw.cab#version=8,5,0,0" width="800" height="600">
    <param name="src" value="idmi.dcr">
	<param name="swStretchStyle" value="fill">
    <param name="AutoStart" value="true">
    <embed src="/web/20040625234530oe_/http://www.poly.edu/huss/idm/idmi.dcr" width="800" height="600" autostart="true" pluginspage="http://www.macromedia.com/shockwave/download/">
</object>
```

In this example, the embedded Shockwave movie file is `idmi.dcr`, which is seen in both the `src` attribute on the `<embed>` tag and the corresponding `<param>` tag under the parent `<object>` tag. By default, the Wayback Machine will rewrite URLs of embedded media files with the `oe_` request flag. When downloading these files, you should append the same flag. 

In most cases, types of different embedded media files can be distinguished by their file extension. A list of legacy media formats commonly seen in web pages from the late 1990s - early 2000s is provided below: 

| Format | File extension |
| :---- | :---- |
| QuickTime | mov |
| RealMedia | ra, rm, ram, rmvb |
| Macromedia Director (Shockwave) | dcr |
| Macromedia Flash | swf |
| VRML | wrl, wrz |


# Case study: scraping Japanese banner ads from 2000



# Further readings

For web archives in historical research, see For a history of web archiving, see Ian Milligan's [Averting the Digital Dark Age: How Archivists, Librarians, and Technologists Built the Web a Memory](https://www.press.jhu.edu/books/title/53671/averting-digital-dark-age).  

The Environmental Data and Governance Initiative (EDGI) produces a Python library aptly named *wayback* that packages a number of Wayback Machine CDX Server API features into Python functions that can be readily imported into your project. Refer to [https://github.com/edgi-govdata-archiving/wayback](https://github.com/edgi-govdata-archiving/wayback) for more information. 

The Memento Framework ...

HTML reference books published in the late 1990s and early 2000s are incredibly helpful for today’s researchers to understand web authoring practices prevalent in that era that are today largely forgotten. Some of the books are now available to borrow on the Internet Archive:
 
 - [HTML Pocket Reference, Second Edition](https://archive.org/details/htmlpocketrefere00nied), written by Jennifer Niederst. Published by O'Reilly and Associates. 
 - [HTML: The Complete Reference, Third Edition](https://archive.org/details/htmlcompleterefe00powe_0/mode/2up), written by Thomas A. Powell. Published by Osborne/McGraw-Hill. 

# Notes
[^1]: Brügger, Niels. “Web History and Social Media.” In The SAGE Handbook of Social Media, edited by Jean Burgess, Alice Marwick, and Thomas Poell. 1 Oliver’s Yard, 55 City Road London EC1Y 1SP: SAGE Publications Ltd, 2018. https://doi.org/10.4135/9781473984066.

[^EDGI-WAYBACK]: “Edgi-Govdata-Archiving/Wayback.” Python. 2019. Reprint, Environmental Data and Governance Initiative, June 11, 2025. https://github.com/edgi-govdata-archiving/wayback.

[^BROWSERWAR]: Castro, Elizabeth. “Chapter 17: Multimedia.” In HTML for the World Wide Web, 293–312. Peachpit Press, 2003.

[^TOOLBAR]: Graham, Mark. “Wayback Machine Playback… Now with Timestamps!” Internet Archive Blogs (blog), October 5, 2017. https://blog.archive.org/2017/10/05/wayback-machine-playback-now-with-timestamps/.

[^TIMESKEW]: Ankerson, Megan Sapnar. “Read/Write the Digital Archive: Strategies for Historical Web Research.” In Digital Research Confidential, edited by Eszter Hargittai and Christian Sandvig, 29–54. The MIT Press, 2015. https://doi.org/10.7551/mitpress/9386.003.0004.

[^REQUESTFLAG]: There appears to be no consensus on the name of this component in archived snapshot URLs on the Wayback Machine. In this lesson, we call them "request flags," which is a term used in the [release notes](https://web.archive.org/web/20231221054022/https://archive-access.sourceforge.net/projects/wayback/release_notes.html) of the Wayback Machine software developed by the Internet Archive. 

[^WAYBACK-MACHINE-NAME]: The Wayback Machine originally referred to only the replay service provided by the Internet Archive for users to browse its archived web content. Today, the term is largely synonymous with the Internet Archive's web archive service, which is also how we are going to use the term in this lesson. For a history of Internet Archive and the Wayback Machine, see Milligan, Ian. Averting the Digital Dark Age: How Archivists, Librarians, and Technologists Built the Web a Memory. 1st ed. Baltimore: Johns Hopkins University Press, 2024. 

# Bibliography


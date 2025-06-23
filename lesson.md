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

In this lesson, you will learn how to scrape images, videos, and other types of media resources from historical web pages archived on the Internet Archive’s Wayback Machine. 

The importance of web archives and archived web data in historical research is getting increasingly recognised as historians turn their attention to the 1990s and early 2000s, a period that saw massive growth and mainstream adoption of the web. While many web archives like the Wayback Machine provide a user-friendly interface for viewing archived snapshots of a single URL, historians looking to perform computational or quantitative analysis may prefer accessing archived web data programmatically in order to examine the availability of archived snapshots of historical URLs, bulk download archived snapshots, and extract specific page elements for further analysis. 

In this lesson, you will learn how to use the Wayback Machine’s CDX Server API to scrape media resources featured on archived snapshots of historical URLs on the Wayback Machine. Specifically, we are going to build a small dataset of historical web banner ads appearing on popular Japanese-language websites in the year 2000. The workflow introduced in the lesson is generally comparable to standard web scraping procedures, but we will cover a number of challenges specific to scraping historical web pages archived on the Wayback Machine - especially non-English web pages from the 1990s and early 2000s. 


# Prerequisites

This lesson is designed for people who have an intermediate level of understanding of Python and HTML. You should ideally have prior experience with web scraping in Python and BeautifulSoup, as well as a basic understanding of how web archives work, though we are going to cover some of the background information in the next section. 

If you are new to Python and HTML, you may want to consult the following Programming Historian lessons on [Python](https://programminghistorian.org/en/lessons/introduction-and-installation) and [HTML](https://programminghistorian.org/en/lessons/viewing-html-files), and subsequent lessons in the series. 

You can follow the lesson on any mainstream operating system you prefer, including Windows, macOS, and popular Linux distributions, as long as you can get a relatively recent version of Python installed on your operating system. At the time of writing, the most recent Python version is 3.13. On Python, you will need to have the following libraries installed: 

- requests  
- BeautifulSoup  
- pillow  
- tenacity 

We recommend that you install Anaconda, a distribution of Python specifically designed for data science research for this lesson. A standard installation of Anaconda includes the first three libraries, and you can easily install tenacity by running `pip install tenacity`. 

# Learning outcomes

By the end of this lesson, you will learn: 

- Using the Wayback Machine CDX Server API to check the available archived snapshots of archived snapshots of a given historical URL.    
- Batch downloading archived web page snapshots from the Wayback Machine.   
- Identifying and downloading web media resources embedded in archived web pages, including common image formats, as well as multimedia content in historical formats, such as Flash, Shockwave, and VRML.   
- Technical limitations and ethical considerations in scraping the Wayback Machine and alternative approaches to using archived web data for quantitative and computational historical research. 


# Course structure

The rest of the lesson is roughly structured into two parts. In the first part, after we outline the learning outcomes and prerequisites, we will briefly review how the Wayback Machine works and introduce the Wayback Machine CDX Server API, which we can use to find all available archived snapshots of a given URL on the Wayback Machine. Next, we will showcase how to detect and scrape different types of media content in an archived web page, with a focus on legacy formats that you may encounter in web pages from the 1990s-early 2000s. 

The second part is the case study where we will use the tools and techniques we introduced in the first part to scrape the Wayback Machine for banner ads appearing on popular Japanese websites. We will discuss 


# Getting Started with Programmatic Access to the Wayback Machine

The earliest institutional attempts to preserve information available on the web started shortly after the web became the main medium for the presentation and transmission of information over the Internet around the mid-1990s. The ensuing years saw the emergence of a range of web archiving initiatives. In this tutorial, we will focus on scraping archived web content on the Wayback Machine. Founded in 1996, the Internet Archive’s Wayback Machine is the world’s first web archive, and today it holds 916 billion web pages from around the world dating back to 1996, publicly accessible through its website at [web.archive.org](http://web.archive.org). 

The Wayback Machine proactively archives the web, mainly by running a web crawler that follows and saves links on the web in a way not dissimilar to search engines. Given its founding date and the worldwide scope of its collection, the Wayback Machine is also the only place where some of the earliest web pages on the Internet may be found. 

You may already know how to access archived snapshots of a given historical URL on the Wayback Machine by entering the URL manually on the Wayback Machine’s home page and then choosing a particular archived snapshot of the URL to view on the Wayback Machine’s calendar interface. While the calendar interface is convenient for manual exploration of single URLs, it becomes impractical when you need to work with a set of URLs, when you want to retrieve multiple archived snapshots of one given URL, or when you need to scrape certain elements from a set of archived web pages. To handle these tasks, you will need a way to access the archive through code rather than through the web interface.

There are different ways to access archived web data on the Wayback Machine programmatically. In this tutorial, we are going to use the Wayback Machine’s CDX Server API to retrieve available archived copies of web resources at a given URL on the Wayback Machine. CDX, or crawl index records, is a metadata index generated during the crawling process describing web data archived by the Wayback Machine’s crawler. Aside from the CDX API, the Wayback Machine can also be queried through the [Memento Protocol API](https://ws-dl.blogspot.com/2013/07/2013-07-15-wayback-machine-upgrades.html) and the [Wayback Machine Availability API](https://archive.org/help/wayback_api.php). All three APIs are available free of charge, though the CDX Server API returns much more information about each archived snapshot of a given URL than the two other alternatives mentioned above, such as HTTP status codes and sizes of the snapshots. 

In addition to APIs, researchers may also be interested in accessing archived web data through integrated research toolkits and platforms such as the Internet Archive’s [Archives Research Compute Hub](https://archive-it.org/arch/). Researchers intending to use these toolkits and platforms generally need to have access to raw archived web data in WARC format or enter a partnership with an archiving organization such as the Internet Archive, but they can provide advanced features such as full-text search and data visualisation. If your research involves a large number of URLs that makes manually scraping impractical, using a research toolkit or platform might be a better choice. 


# Downloading archived web pages from the Wayback Machine

The tools and methods to scrape media resources off archived web pages on the Wayback Machine do not differ much technically from those commonly used to scrape the live web. However, to ensure that we can interpret scraped archived web data correctly, it is important to know how the Wayback Machine saves content on the web, and how it serves archived web content to the user on its web interface. 

# Understanding web archive replay and time skew

Web archive scholars have long emphasized that archived web content differs significantly from traditional archival materials. As Niels Brügger notes, an archived web page is "better understood as an actively created and subjective reconstruction" of what the original page may have looked like at a given point in time. The way an archived web page is *reconstructed* has implications for how we scrape, analyze, and interpret archived web content, which we will outline in the rest of this section. 

A typical web page consists of a primary HTML document that defines its structure and textual content, along with numerous auxiliary resources such as images, stylesheets, scripts, and other media files. These resources are referenced in the HTML document by their own URLs. For example, an image in a web page is usually embedded using the `<img>` tag, with the image file’s location specified in the src attribute (e.g., `<img src="images/logo.gif">`). Similarly, stylesheets and scripts are linked using `<link>` and `<script>` tags. To display the page correctly, the browser must fetch all of these external resources in addition to the main HTML file. 

When the Wayback Machine archives a web page, it attempts to archive both the HTML and all linked resources. However, if the Wayback Machine served archived HTML files exactly as they were originally written, the browser would try to fetch all linked resources from their original locations on the live web. Because many of these resources no longer exist online, this would result in broken images, missing styles, or incomplete functionality. To address this, the Wayback Machine modifies the HTML source by rewriting each resource URL to point to its archived version. This ensures that pages load as completely as possible using content from the archive rather than the live web.

This process of dynamically assembling and serving an archived page by combining its HTML with available archived resources is called **replay**. During replay, the Wayback Machine retrieves the archived HTML file, rewrites URLs to point to corresponding resources in the archive, and presents the reconstructed page to the user \- often with a toolbar interface for navigation and metadata.

Ideally, all resources on a web page would all be archived at the same moment as the HTML file. In practice, however, technical limitations often prevent the archive from capturing every resource at once. As a result, the Wayback Machine makes a “best effort” replay by stitching together the HTML file with the closest available versions of its linked resources from other capture dates. In some cases, elements appearing in a reconstructed page may have been archived days, months, or even years apart. This temporal incoherence is sometimes referred to as *time skew*. For researchers intending to use archived web content as source materials, time skews can complicate efforts to interpret a page’s content or intended user experience as it originally appeared on the web.

In the case study section, we present a general workflow for scraping media from archived web pages on the Wayback Machine. This workflow is designed with these archival quirks in mind, helping researchers identify, retrieve, and interpret media resources while accounting for time skews. The lesson is specifically geared towards web pages from the late 1990s \- early 2000s. Interested researchers can consult the relevant literature we include in the further readings section to learn more about technical issues in web archive replay. 


# Anatomy of an archived web page

To better understand how the Wayback Machine serves archived web content, let’s observe an archived snapshot of Google’s home page saved by the Wayback Machine in 1999, available at [https://web.archive.org/web/19990117032727/http://www.google.com/](https://web.archive.org/web/19990117032727/http://www.google.com/). 

We can begin by looking at the URL itself. Typically, the URL of an archived web resource on the Wayback Machine looks like this:

```
https://web.archive.org/web/[timestamp in yyyymmddhhmmss][optional request flag]/[original URL]
```

The timestamp in the URL is in Coordinated Universal Time (UTC). Therefore, this particular snapshot of Google’s home page \- whose original URL is http://www.google.com \- was captured on January 17, 1999, 03:27:27 UTC. The timestamp is sometimes followed by an optional request flag, whose role we will explain shortly. 

Note that if you provide an incomplete timestamp, or a timestamp on which the Wayback Machine does not have an archived snapshot of the given URL, the Wayback Machine will automatically find and return the snapshot captured at the closest available timestamp to the one given. For example, if you visit [https://web.archive.org/web/**19990116**/http://www.google.com/](https://web.archive.org/web/19990116/http://www.google.com/), the Wayback Machine will automatically redirect you to the archived snapshot of [google.com](http://Google.com) captured at the closest available timestamp to 19990116, which is 19990117032727. 

Open the link in your browser, and you will be greeted with an archived version of Google’s homepage in 1999.

{% include figure.html filename="google-screenshot-1.png" alt="A screenshot of a Wayback Machine capture of google.com made on January 17, 1999, 03:27:27 UTC" caption="Wayback Machine capture of google.com made on January 17, 1999" %}

The first thing you may notice on the page \- apart from how different Google looked back then \- is the existence of a toolbar on the top of the page. The toolbar allows you to quickly navigate between archived snapshots captured at different points in time. The toolbar also allows(https://blog.archive.org/2017/10/05/wayback-machine-playback-now-with-timestamps/) you to view timestamps of linked resources on the archived web page by clicking “About this capture”, which should give you a sense of to what degree the page suffers from time skew. 

\[SCREENSHOT \- about this capture\]

In our case, we can see that the Google logo \- the only image file on the page \- is actually archived 3 months 17 days from the timestamp of the current snapshot. While this is technically a case of time skew, we can be sure that the logo should be identical to what may have been displayed on Google’s website on the date of the page snapshot by triangulating with [other](https://doodles.google/doodle/google-beta/) sources. 

Next, we can examine the source code of the archived web page using the inspector, which is a browser feature that allows us to view elements on the page and their corresponding sections in the HTML source code. On most browsers, you can press Ctrl+Shift+I (Windows/Linux) or Cmd+Option+I (Mac) to open the inspector. 

\[SCREENSHOT \- hyperlink\]

We can see that all hyperlinks on the page have been rewritten with a prefix `/web/19990117032727`. This allows you to follow links on the web page and navigate to the closest available snapshot of the linked page, as if you were browsing the live web in 1999\. Also note that the `src` attribute of the `<img>` element representing the Google logo is "/web/19990117032727im\_/[http://www.google.com/google.jpg](http://www.google.com/google.jpg)". The “/web/19990117032727im\_/” part is added by the Wayback Machine. This means that when your browser is loading the web page, the Google logo image is not loaded from the original URL (“[http://www.google.com/google.jpg](http://www.google.com/google.jpg)”), but its archived version on the Wayback Machine \- the full URL of the archived logo image is [https://web.archive.org/web/19990117032727im\_/http://www.google.com/google.jpg](https://web.archive.org/web/19990117032727im_/http://www.google.com/google.jpg). If you open the image link URL directly in your web browser, you will see that the Wayback Machine automatically redirected the URL to [https://web.archive.org/web/19990504112211im\_/http://www.google.com/google.jpg](https://web.archive.org/web/19990504112211im_/http://www.google.com/google.jpg), which is the closest available archived copy of the image file that the Wayback Machine could find. The time difference between the timestamp in the new URL (19990504112211) and the timestamp in the URL before redirection (19990117032727) corresponds to the 3 month 17 days time difference reported on the Wayback Machine toolbar. We can therefore obtain information about the archival date of each individual resource on the page and assess the extent of time skew by comparing the timestamps of the reconstructed page and its component resources. 

Lastly, you may notice the rewritten image URL contains a request flag `im_`.  A request flag is a special modifier inserted between the timestamp and the original URL in a Wayback Machine link. It controls how the archived content is served during replay. In this particular case, the flag `im_` instructs the Wayback Machine to return the archived resource as-is without applying any kind of modifications, which allows the browser to load the image correctly in the archived web page. `im_` is also applied to media resources like audio and video files. Below is a list of other request flags that you may encounter in archived web pages: 

- cs\_ and js\_: These flags are usually added to CSS and JavaScript files. Wayback Machine will rewrite any URLs in these files to their archived versions according to the timestamp provided, and add a note of archival capture information to the file. To retrieve CSS and JS files as they are originally archived, use the id\_ flag as described below.   
- oe\_: Similar to im\_, but is used for embedded objects like Flash, Shockwave, etc. 

Researchers scraping the Wayback Machine may find the following two flags useful in some scenarios: 

- id\_: Adding the id\_ flag forces the Wayback Machine to return an archived web page as-is, without modifying any URLs in the document. This will cause many in-page resources to fail to load in a browser, but it allows researchers to analyze the original HTML exactly as it was archived \- useful for studying the structure, authoring practices, or embedded metadata of historical web pages without interference from replay modifications.  
- if\_: Adding the if\_ flag effectively removes the Wayback Machine toolbar from an archived web page, but the URLs of resources and hyperlinks will still be rewritten. Useful for capturing screenshots, or if you want to take advantage of the rewritten URLs during the scraping process. 
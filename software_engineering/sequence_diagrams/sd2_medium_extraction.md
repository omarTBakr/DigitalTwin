# SD-2. Medium extraction inside a crawl step (implemented)

[← Sequence diagrams](README.md) · [Hub](../README.md) · Previous: [SD-1](sd1_etl_pipeline_run.md) · Next: [SD-3](sd3_trigger_incremental_etl.md)

| | |
|---|---|
| Status | Implemented (P0) |
| Requirements | [ETL](../requirements/requirements.md#23-extraction-framework-etl) 002, 008 · [MED](../requirements/requirements.md#medium-med) 001, 002, 003, 004, 005, 006 |
| User stories | US-016, US-019, US-023, US-024, US-025 ([backlog](../user_stories/user_stories.md)) |
| Use cases | [UC-07](../use_cases/02_run_etl.md#uc-07-extract-content-from-a-provider) |
| Class diagrams | [3a](../class_diagrams/03a_extraction_framework.md), [3b](../class_diagrams/03b_providers_medium_and_github.md), [3c](../class_diagrams/03c_providers_linkedin_obsidian_and_articles.md) |
| draw.io | copy the ```mermaid block below → Arrange › Insert › Mermaid |


The detail of `MediumExtractor` for one `medium_tag` source and one `medium_author` source. Article text comes only from official RSS feeds (FR-MED-001). The browser is started only if a tag source is selected, and only discovers links.

```mermaid
sequenceDiagram
  autonumber
  participant Crawl as crawl_provider
  participant Ext as MediumExtractor
  participant Feeds as MediumFeedClient
  participant Listing as MediumListingPage
  participant Browser as Browser (Selenium)
  participant Medium as medium.com

  Crawl->>Ext: extract()
  Ext->>Ext: session(): counts = context.topic_counts(), known topics per doc
  Ext->>Feeds: open (pacing feed_delay_s, backoff on 429/5xx)
  opt any medium_tag source selected
    Ext->>Browser: open profile (headed or headless)
  end

  Note over Ext: medium_tag source
  Ext->>Ext: all topics at cap? then skipped, next source
  alt browser available and not blocked
    Ext->>Listing: collect(tag listing_url, limit = missing x 2)
    Listing->>Browser: open(url) then wheel scroll_down with pauses
    Browser->>Medium: GET /tag/<tag>/recommended
    alt bot challenge does not clear
      Browser-->>Ext: AccessBlockedError
      Ext->>Ext: listing_blocked = true (no browser for the rest of the run)
      Ext->>Feeds: tag_feed(tag)
      Feeds->>Medium: GET /feed/tag/<tag>
    else page loads
      Listing-->>Ext: article links
    end
  else
    Ext->>Feeds: tag_feed(tag)
    Feeds->>Medium: GET /feed/tag/<tag>
  end
  loop each discovered link (until topics at cap)
    Ext->>Ext: feed_url_for_article(url) (author or publication feed)
    Ext->>Feeds: entries(feed_url) (cached per run)
    Feeds->>Medium: GET /feed/@author
    alt article not in the feed (older than ~10 posts)
      Ext->>Ext: record_skipped(not in feed)
    else found
      Ext->>Ext: _accept: duplicate? member-only? topics at cap?
      Ext-->>Crawl: RawDocument (origin external, crawler medium_rss)
    end
  end
  Note over Ext,Feeds: planned MED-005: RateLimitError stops the provider here, Retry-After honoured
  Note over Ext,Browser: planned MED-008: unattended runs never start the browser

  Note over Ext: medium_author source
  Ext->>Feeds: author_feed(@handle)
  Feeds->>Medium: GET /feed/@handle
  loop each entry
    Ext->>Ext: _accept (free posts have full text, member-only skipped)
    Ext-->>Crawl: RawDocument
  end
  Ext->>Browser: quit (session exit)
  Ext->>Feeds: close
```

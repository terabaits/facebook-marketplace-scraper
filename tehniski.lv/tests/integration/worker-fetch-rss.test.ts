import { describe, it, expect, vi, afterEach } from 'vitest';
import { parseRssFeed, ParsedItem } from '~worker/rss/parser';
import { urlHash, contentHash, partitionBySeen } from '~worker/rss/dedupe';
import { scrapeWithCheerio } from '~worker/scrapers/cheerio-scraper';

// Inline fixtures — no network calls, deterministic.
const FIXTURE_RSS = `<?xml version="1.0"?>
<rss version="2.0">
<channel>
<title>Fixture Feed</title>
<link>https://fixture.example.com</link>
<description>Integration test feed</description>
<item>
<title>Fixture article one</title>
<link>https://fixture.example.com/news/one</link>
<guid>https://fixture.example.com/news/one</guid>
<pubDate>Wed, 26 Aug 2026 10:00:00 GMT</pubDate>
<description>One</description>
</item>
<item>
<title>Fixture article two</title>
<link>https://fixture.example.com/news/two</link>
<pubDate>2026-08-26T11:00:00Z</pubDate>
</item>
</channel>
</rss>`;

const FIXTURE_HTML = `<!doctype html>
<html lang="en">
<head><title>Fixture article one</title></head>
<body>
<article>
  <h1>Fixture article one</h1>
  <p>Hello from the integration fixture. This is the first paragraph with enough words to count as content.</p>
  <h2>A subsection</h2>
  <p>Another paragraph that adds more words to the article body so the markdown extractor has something to work with.</p>
  <ul>
    <li>First bullet point about the topic</li>
    <li>Second bullet point with additional info</li>
  </ul>
</article>
</body>
</html>`;

describe('worker integration: parse + dedupe (offline, fixture-only)', () => {
  it('parses the inline RSS fixture', () => {
    const items = parseRssFeed(FIXTURE_RSS, 'https://fixture.example.com/feed.xml');
    expect(items).toHaveLength(2);
    expect(items[0].url).toBe('https://fixture.example.com/news/one');
    expect(items[0].title).toBe('Fixture article one');
    expect(items[1].guid).toBe('https://fixture.example.com/news/two'); // link fallback
    for (const item of items) {
      expect(item.url).toMatch(/^https?:\/\//);
      expect(urlHash(item.url)).toMatch(/^[0-9a-f]{64}$/);
    }
  });

  it('partitions new vs seen using urlHash', () => {
    const items = parseRssFeed(FIXTURE_RSS, 'https://fixture.example.com/feed.xml');
    // Pre-load one item as already-seen (simulating the DB lookup)
    const existing = new Set([urlHash(items[0].url)]);
    const { newItems } = partitionBySeen(
      items.map((i) => ({ url: i.url, title: i.title, urlHash: () => urlHash(i.url) })),
      existing
    );
    expect(newItems).toHaveLength(1);
    expect(newItems[0].url).toBe(items[1].url);
  });

  it('contentHash is stable across calls', () => {
    const items = parseRssFeed(FIXTURE_RSS, 'https://fixture.example.com/feed.xml');
    const a = contentHash(items[0].title + items[0].description);
    const b = contentHash(items[0].title + items[0].description);
    expect(a).toBe(b);
    expect(contentHash('x')).not.toBe(contentHash('y'));
  });
});

describe('worker integration: scrape (mocked fetch, no real network)', () => {
  const originalFetch = globalThis.fetch;
  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('extracts markdown from a fixed HTML body', async () => {
    // Mock global fetch to return the inline HTML body, no real network.
    const fetchMock = vi.fn(async (url: string) => {
      return new Response(FIXTURE_HTML, {
        status: 200,
        headers: { 'content-type': 'text/html' }
      });
    });
    globalThis.fetch = fetchMock as any;

    const article = await scrapeWithCheerio('https://fixture.example.com/news/one');
    // Title and at least some content
    expect(article.title.toLowerCase()).toContain('fixture');
    expect(article.markdown).toContain('Hello from the integration fixture');
    expect(article.markdown).toContain('## A subsection');
    expect(article.markdown).toContain('- First bullet point about the topic');
    expect(article.word_count).toBeGreaterThan(0);
    // Readability may extract an author; we accept either an author or undefined
    expect(['string', 'undefined']).toContain(typeof article.author);
    // fetch was called exactly once with the article URL
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('throws on a non-2xx response', async () => {
    globalThis.fetch = vi.fn(async () => new Response('not found', { status: 404 })) as any;
    await expect(scrapeWithCheerio('https://fixture.example.com/missing')).rejects.toThrow(/404/);
  });
});

describe('worker integration: end-to-end pipeline (RSS → dedupe → scrape → scraped_stories shape)', () => {
  const originalFetch = globalThis.fetch;
  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('produces a ScrapedStory-shaped object for each new item', async () => {
    globalThis.fetch = vi.fn(async (url: string) => {
      if (url.endsWith('/feed.xml') || url.includes('rss')) {
        return new Response(FIXTURE_RSS, { status: 200, headers: { 'content-type': 'application/rss+xml' } });
      }
      return new Response(FIXTURE_HTML, { status: 200, headers: { 'content-type': 'text/html' } });
    }) as any;

    // 1) Fetch + parse the RSS
    const rssRes = await fetch('https://fixture.example.com/feed.xml');
    const xml = await rssRes.text();
    const items: ParsedItem[] = parseRssFeed(xml, 'https://fixture.example.com/feed.xml');
    expect(items.length).toBeGreaterThan(0);

    // 2) Dedupe (none seen yet)
    const seen = new Set<string>();
    const { newItems } = partitionBySeen(
      items.map((i) => ({ ...i, urlHash: () => urlHash(i.url) })),
      seen
    );
    expect(newItems.length).toBe(items.length);

    // 3) Scrape each new item, build a ScrapedStory-shaped row
    const rows: any[] = [];
    for (const item of newItems) {
      const article = await scrapeWithCheerio(item.url);
      const hash = urlHash(item.url);
      rows.push({
        source_id: 'fixture-source',
        url: item.url,
        url_hash: hash,
        content_hash: contentHash(article.markdown),
        title: item.title,
        author: article.author ?? null,
        published_at_src: item.published_at,
        scraped_at: new Date(),
        markdown: article.markdown,
        summary: article.markdown.slice(0, 500),
        word_count: article.word_count,
        language: 'en'
      });
    }
    expect(rows).toHaveLength(items.length);
    for (const row of rows) {
      // shape matches ScrapedStory create-input
      expect(row.url_hash).toMatch(/^[0-9a-f]{64}$/);
      expect(row.content_hash).toMatch(/^[0-9a-f]{64}$/);
      expect(row.url).toMatch(/^https?:\/\//);
      expect(typeof row.markdown).toBe('string');
      expect(row.word_count).toBeGreaterThan(0);
    }
  });
});

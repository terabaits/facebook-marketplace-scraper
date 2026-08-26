import { describe, it, expect } from 'vitest';
import { parseRssFeed } from '~worker/rss/parser';

const SAMPLE_RSS = `<?xml version="1.0"?>
<rss version="2.0">
<channel>
<title>Test Feed</title>
<link>https://example.com</link>
<description>Test</description>
<item>
<title>First article</title>
<link>https://example.com/first</link>
<guid>https://example.com/first</guid>
<pubDate>Wed, 26 Aug 2026 10:00:00 GMT</pubDate>
<description>First article body</description>
</item>
<item>
<title>Second article</title>
<link>https://example.com/second</link>
<pubDate>2026-08-26T11:00:00Z</pubDate>
</item>
</channel>
</rss>`;

describe('parseRssFeed', () => {
  it('parses a basic RSS 2.0 feed', () => {
    const items = parseRssFeed(SAMPLE_RSS, 'https://example.com/feed');
    expect(items).toHaveLength(2);
    expect(items[0]).toMatchObject({
      url: 'https://example.com/first',
      title: 'First article',
      guid: 'https://example.com/first'
    });
    expect(items[0].published_at).toBeInstanceOf(Date);
  });
  it('handles missing guid by using link as fallback', () => {
    const items = parseRssFeed(SAMPLE_RSS, 'https://example.com/feed');
    expect(items[1].guid).toBe('https://example.com/second');
  });
  it('skips items without a link', () => {
    const xml = `<rss version="2.0"><channel><item><title>no link</title></item></channel></rss>`;
    const items = parseRssFeed(xml, 'x');
    expect(items).toEqual([]);
  });
  it('throws on invalid XML', () => {
    expect(() => parseRssFeed('<not-xml', 'x')).toThrow();
  });
});

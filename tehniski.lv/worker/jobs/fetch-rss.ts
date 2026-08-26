import cron from 'node-cron';
import { db } from '../lib/db.js';
import { log } from '../lib/logger.js';
import { parseRssFeed } from '../rss/parser.js';
import { urlHash, contentHash } from '../rss/dedupe.js';
import { scrapeForSource, trackScrapeSuccess, trackScrapeFailure } from '../scrapers/index.js';

async function fetchAndScrapeSource(sourceId: string) {
  const source = await db.rssSource.findUnique({ where: { id: sourceId } });
  if (!source || !source.active) return;
  log.info('[fetch-rss] source start', { source: source.name });
  try {
    const res = await fetch(source.feed_url, {
      headers: { 'User-Agent': 'tehniski.lv/0.2 (+https://tehniski.lv/bot)' },
      redirect: 'follow'
    });
    if (!res.ok) throw new Error(`feed fetch ${source.feed_url} → ${res.status}`);
    const xml = await res.text();
    const items = parseRssFeed(xml, source.feed_url);
    const seenHashes = new Set<string>(
      (await db.scrapedStory.findMany({
        where: { url_hash: { in: items.map((i) => urlHash(i.url)) } },
        select: { url_hash: true }
      })).map((r) => r.url_hash)
    );
    const newItems = items.filter((i) => !seenHashes.has(urlHash(i.url)));
    log.info('[fetch-rss] source', { source: source.name, total: items.length, new: newItems.length });
    let success = 0, failed = 0;
    for (const item of newItems) {
      try {
        const scraped = await scrapeForSource(item.url, source.parser_config);
        const hash = urlHash(item.url);
        const body = scraped.markdown;
        const ch = contentHash(body);
        await db.scrapedStory.upsert({
          where: { url_hash: hash },
          update: {
            title: item.title,
            author: item.author,
            published_at_src: item.published_at,
            markdown: body,
            summary: body.slice(0, 500),
            word_count: scraped.word_count,
            language: 'en'
          },
          create: {
            source_id: source.id,
            url: item.url,
            url_hash: hash,
            content_hash: ch,
            title: item.title,
            author: item.author,
            published_at_src: item.published_at,
            markdown: body,
            summary: body.slice(0, 500),
            word_count: scraped.word_count,
            language: 'en'
          }
        });
        success++;
      } catch (e: any) {
        log.warn('[fetch-rss] item failed', { url: item.url, error: e.message });
        failed++;
      }
    }
    await trackScrapeSuccess(source.id);
    log.info('[fetch-rss] source done', { source: source.name, success, failed });
  } catch (e: any) {
    log.error('[fetch-rss] source error', { source: source.name, error: e.message });
    await trackScrapeFailure(source.id, e.message);
  }
}

export async function fetchAllActiveSources() {
  const sources = await db.rssSource.findMany({ where: { active: true } });
  for (const s of sources) {
    await fetchAndScrapeSource(s.id);
    // tiny stagger to be polite to upstream servers
    await new Promise((r) => setTimeout(r, 2000));
  }
}

export function startFetchRss() {
  return cron.schedule('0 */3 * * *', () => {
    log.info('[fetch-rss] cron tick');
    fetchAllActiveSources().catch((e) => log.error('[fetch-rss] cron error', { error: e.message }));
  });
}

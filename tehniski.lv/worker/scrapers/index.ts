import { db } from '../lib/db.js';
import { scrapeWithCheerio, ScrapedArticle } from './cheerio-scraper.js';
import { scrapeWithPlaywright } from './playwright-scraper.js';

export async function scrapeForSource(url: string, parserConfig: any): Promise<ScrapedArticle> {
  const kind = parserConfig?.kind ?? 'readability';
  if (kind === 'playwright') return scrapeWithPlaywright(url);
  return scrapeWithCheerio(url);
}

export async function trackScrapeSuccess(sourceId: string) {
  await db.rssSource.update({
    where: { id: sourceId },
    data: { last_fetched_at: new Date(), last_error: null, scrape_count: { increment: 1 } }
  });
}

export async function trackScrapeFailure(sourceId: string, error: string) {
  await db.rssSource.update({ where: { id: sourceId }, data: { last_error: error.slice(0, 500) } });
}

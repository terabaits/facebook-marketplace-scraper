import type { Browser, BrowserContext } from 'playwright';
import { ScrapedArticle } from './cheerio-scraper.js';
import { Readability } from '@mozilla/readability';
import { JSDOM } from 'jsdom';

let browserPromise: Promise<Browser> | null = null;
async function getBrowser(): Promise<Browser> {
  if (!browserPromise) {
    const { chromium } = await import('playwright');
    browserPromise = chromium.launch({ headless: true });
  }
  return browserPromise;
}

export async function scrapeWithPlaywright(url: string): Promise<ScrapedArticle> {
  const browser = await getBrowser();
  const context: BrowserContext = await browser.newContext({ userAgent: 'tehniski.lv/0.2 (+https://tehniski.lv/bot)' });
  const page = await context.newPage();
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30_000 });
    // Wait for one network-idle period (most JS-rendered sites finish within 2s)
    await page.waitForLoadState('networkidle', { timeout: 5_000 }).catch(() => {});
    const html = await page.content();
    const virtualDom = new JSDOM(html, { url });
    const reader = new Readability(virtualDom.window.document);
    const article = reader.parse();
    if (!article) throw new Error(`Playwright: Readability returned no article for ${url}`);
    const cheerio = await import('cheerio');
    const $ = cheerio.load(article.content ?? '');
    const lines: string[] = [];
    $('h1, h2, h3, p, li, pre').each((_, el) => {
      // Cheerio's .each() callback gets an AnyNode; only Element has tagName.
      if (!el || !('tagName' in el)) return;
      const $el = $(el);
      const text = $el.text().trim();
      if (!text) return;
      const tag = (el as { tagName: string }).tagName.toLowerCase();
      if (tag === 'h1') lines.push(`# ${text}`);
      else if (tag === 'h2') lines.push(`## ${text}`);
      else if (tag === 'h3') lines.push(`### ${text}`);
      else if (tag === 'pre') lines.push('```\n' + text + '\n```');
      else if (tag === 'li') lines.push(`- ${text}`);
      else lines.push(text);
      lines.push('');
    });
    const markdown = lines.join('\n').replace(/\n{3,}/g, '\n\n').trim();
    return { title: article.title ?? '', author: article.byline ?? undefined, markdown, word_count: markdown.split(/\s+/).filter(Boolean).length };
  } finally {
    await context.close();
  }
}

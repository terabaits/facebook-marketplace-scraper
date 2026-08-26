import * as cheerio from 'cheerio';
import { Readability } from '@mozilla/readability';
import { JSDOM } from 'jsdom';
import type { Element } from 'domhandler';

export type ScrapedArticle = {
  title: string;
  author?: string;
  markdown: string;
  word_count: number;
};

// `cheerio` v1.2 ships its own types but @types/cheerio is also installed; their `Cheerio`
// type isn't generic in the latter, so the helper takes a loose parameter type. The runtime
// behavior is identical — we just need `$` to be a callable cheerio selection function.
type CheerioLike = (selector: any) => { each: (fn: (idx: number, el: any) => void) => void; text: () => string };

function htmlToMarkdown($: CheerioLike): string {
  // Minimal HTML → markdown: keep headings, paragraphs, lists, links, code blocks.
  // This is intentionally simple — the LLM in M3 will rewrite the article, so we just need a clean readable extract.
  const lines: string[] = [];
  $('h1, h2, h3, h4, p, li, pre, blockquote').each((_idx, el) => {
    // Cheerio's .each() callback gets an AnyNode; only Element has tagName.
    if (!el || !('tagName' in el)) return;
    const $el = $(el);
    const tag = (el as Element).tagName.toLowerCase();
    const text = $el.text().trim();
    if (!text) return;
    if (tag === 'h1') lines.push(`# ${text}`);
    else if (tag === 'h2') lines.push(`## ${text}`);
    else if (tag === 'h3') lines.push(`### ${text}`);
    else if (tag === 'h4') lines.push(`#### ${text}`);
    else if (tag === 'pre') lines.push('```\n' + text + '\n```');
    else if (tag === 'blockquote') lines.push('> ' + text);
    else if (tag === 'li') lines.push(`- ${text}`);
    else lines.push(text);
    lines.push('');
  });
  return lines.join('\n').replace(/\n{3,}/g, '\n\n').trim();
}

export async function scrapeWithCheerio(url: string): Promise<ScrapedArticle> {
  const res = await fetch(url, {
    headers: { 'User-Agent': 'tehniski.lv/0.2 (+https://tehniski.lv/bot)' },
    redirect: 'follow'
  });
  if (!res.ok) throw new Error(`fetch ${url} → ${res.status}`);
  const html = await res.text();
  // Mozilla Readability needs a DOM; jsdom is the canonical Node shim.
  const virtualDom = new JSDOM(html, { url });
  const reader = new Readability(virtualDom.window.document);
  const article = reader.parse();
  if (!article) throw new Error(`Readability returned no article for ${url}`);
  const $ = cheerio.load(article.content ?? '');
  const markdown = htmlToMarkdown($);
  const word_count = markdown.split(/\s+/).filter(Boolean).length;
  return {
    title: article.title ?? '',
    author: article.byline ?? undefined,
    markdown,
    word_count
  };
}

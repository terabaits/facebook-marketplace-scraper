import { XMLParser } from 'fast-xml-parser';

export type ParsedItem = {
  url: string;
  title: string;
  author?: string;
  published_at: Date;
  guid: string;
  description?: string;
};

const parser = new XMLParser({
  ignoreAttributes: false,
  attributeNamePrefix: '',
  textNodeName: '#text'
});

export function parseRssFeed(xml: string, feedUrl: string): ParsedItem[] {
  let doc: any;
  try {
    doc = parser.parse(xml);
  } catch (e) {
    throw new Error(`Invalid RSS XML from ${feedUrl}: ${(e as Error).message}`);
  }
  const channel = doc?.rss?.channel;
  if (!channel) return [];
  const rawItems = Array.isArray(channel.item) ? channel.item : (channel.item ? [channel.item] : []);
  const items: ParsedItem[] = [];
  for (const it of rawItems) {
    const link = (it.link ?? '').toString().trim();
    if (!link) continue;
    const title = (it.title ?? '').toString().trim() || link;
    const guid = (it.guid ?? link).toString().trim();
    const pubStr = (it.pubDate ?? it['dc:date'] ?? '').toString();
    const published_at = pubStr ? new Date(pubStr) : new Date();
    if (isNaN(published_at.getTime())) continue;
    const author = it['dc:creator'] ? it['dc:creator'].toString() : (it.author ?? undefined);
    const description = it.description ? it.description.toString() : undefined;
    items.push({ url: link, title, author, published_at, guid, description });
  }
  return items;
}

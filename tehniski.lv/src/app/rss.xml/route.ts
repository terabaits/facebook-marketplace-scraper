import { db } from '@/lib/db';

export async function GET() {
  const posts = await db.post.findMany({
    where: { status: 'published', deleted_at: null },
    orderBy: { published_at: 'desc' },
    take: 50
  });
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:5002';
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>tehniski.lv</title>
<link>${siteUrl}</link>
<description>Latvian tech news</description>
<language>lv</language>
${posts.map(p => `
<item>
<title>${escapeXml(p.title)}</title>
<link>${siteUrl}/post/${p.slug}</link>
<guid>${siteUrl}/post/${p.slug}</guid>
<pubDate>${p.published_at!.toISOString()}</pubDate>
<description>${escapeXml(p.excerpt)}</description>
</item>`).join('')}
</channel>
</rss>`;
  return new Response(xml, { headers: { 'Content-Type': 'application/rss+xml; charset=utf-8' } });
}

function escapeXml(s: string): string {
  return s.replace(/[<>&'"]/g, c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', "'": '&apos;', '"': '&quot;' }[c]!));
}

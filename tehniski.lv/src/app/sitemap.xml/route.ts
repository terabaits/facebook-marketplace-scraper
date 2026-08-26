import { db } from '@/lib/db';

export async function GET() {
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:5002';
  const posts = await db.post.findMany({ where: { status: 'published', deleted_at: null }, select: { slug: true, updated_at: true } });
  const categories = await db.category.findMany({ select: { slug: true } });
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>${siteUrl}</loc></url>
${categories.map(c => `<url><loc>${siteUrl}/category/${c.slug}</loc></url>`).join('\n')}
${posts.map(p => `<url><loc>${siteUrl}/post/${p.slug}</loc><lastmod>${p.updated_at.toISOString()}</lastmod></url>`).join('\n')}
</urlset>`;
  return new Response(xml, { headers: { 'Content-Type': 'application/xml; charset=utf-8' } });
}

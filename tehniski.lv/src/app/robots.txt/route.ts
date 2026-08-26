export function GET() {
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:5002';
  return new Response(`User-agent: *\nAllow: /\nSitemap: ${siteUrl}/sitemap.xml\n`, {
    headers: { 'Content-Type': 'text/plain' }
  });
}

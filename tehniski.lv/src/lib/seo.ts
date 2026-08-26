export function articleJsonLd(post: { title: string; excerpt: string; slug: string; published_at: Date | null; author: { name: string }; cover_image_url: string | null }) {
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:5002';
  return {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: post.title,
    description: post.excerpt,
    image: post.cover_image_url ? [post.cover_image_url] : undefined,
    datePublished: post.published_at?.toISOString(),
    dateModified: post.published_at?.toISOString(),
    author: [{ '@type': 'Person', name: post.author.name }],
    publisher: { '@type': 'Organization', name: 'tehniski.lv' },
    mainEntityOfPage: { '@type': 'WebPage', '@id': `${siteUrl}/post/${post.slug}` }
  };
}

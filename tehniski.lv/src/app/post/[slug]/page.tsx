import { db } from '@/lib/db';
import { notFound } from 'next/navigation';
import { headers } from 'next/headers';
import { AdSlot } from '@/components/ad-slot';
import { CommentSection } from '@/components/comment-section';
import { MoreFromSection } from '@/components/more-from-section';
import { PostDetailActions } from '@/components/post-detail-actions';
import { formatDateLv } from '@/lib/format';
import { lv } from '@/lib/lv';
import { articleJsonLd } from '@/lib/seo';
import { recordPostView } from '@/lib/analytics';
import type { Metadata } from 'next';

export const revalidate = 60;

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug: rawSlug } = await params;
  const slug = decodeURIComponent(rawSlug);
  const post = await db.post.findUnique({ where: { slug }, select: { title: true, excerpt: true } });
  if (!post) return {};
  return { title: `${post.title} — tehniski.lv`, description: post.excerpt };
}

export default async function PostPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug: rawSlug } = await params;
  const slug = decodeURIComponent(rawSlug);
  const post = await db.post.findFirst({
    where: { slug, status: 'published', deleted_at: null },
    include: { author: true, category: true, _count: { select: { comments: true } } }
  });
  if (!post) notFound();

  // Record a view (best-effort; don't block render on dedup miss)
  const h = await headers();
  const ip = h.get('x-forwarded-for') ?? '0.0.0.0';
  const ua = h.get('user-agent') ?? '';
  const ref = h.get('referer') ?? undefined;
  recordPostView(post.id, ip, ua, ref).catch(() => {});

  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:5002';
  const postUrl = `${siteUrl}/post/${post.slug}`;

  return (
    <article className="max-w-6xl mx-auto px-4 py-8">
      <div className="mb-6"><AdSlot slotKey="post_top" /></div>
      <div className="font-mono text-xs text-text-secondary mb-2">
        {post.category?.name ?? 'Vispārīgi'} · {formatDateLv(post.published_at ?? new Date())} · 💬 {lv.plural.comments(post._count.comments)}
      </div>
      <h1 className="text-4xl font-bold mb-3">{post.title}</h1>
      <p className="text-lg text-text-secondary mb-6">{post.excerpt}</p>
      <div className="grid grid-cols-12 gap-6">
        <div className="col-span-9">
          {post.cover_image_url && (
            <img src={post.cover_image_url} alt={post.cover_image_alt ?? post.title} className="w-full rounded-md mb-6" />
          )}
          <div className="prose prose-invert max-w-none" dangerouslySetInnerHTML={{ __html: post.content_html }} />
          <PostDetailActions url={postUrl} title={post.title} sourceUrl={post.source_url} />
          <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(articleJsonLd(post)) }} />
        </div>
        <aside className="col-span-3">
          <div className="sticky top-4"><AdSlot slotKey="post_right_rail" /></div>
        </aside>
      </div>
      <CommentSection postId={post.id} postSlug={post.slug} />
      <MoreFromSection postId={post.id} categoryId={post.category_id} />
    </article>
  );
}

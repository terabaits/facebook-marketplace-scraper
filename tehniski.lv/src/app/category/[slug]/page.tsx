import { db } from '@/lib/db';
import { notFound } from 'next/navigation';
import { PostCard } from '@/components/post-card';

export const revalidate = 60;

export default async function CategoryPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug: rawSlug } = await params;
  const slug = decodeURIComponent(rawSlug);
  const category = await db.category.findUnique({ where: { slug } });
  if (!category) notFound();
  const posts = await db.post.findMany({
    where: { status: 'published', deleted_at: null, category_id: category.id },
    orderBy: { published_at: 'desc' },
    take: 30,
    include: { _count: { select: { comments: true } } }
  });
  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">{category.name}</h1>
      <div className="grid grid-cols-12 gap-6">
        {posts.map(p => <PostCard key={p.id} post={p as any} size="small" />)}
      </div>
    </div>
  );
}

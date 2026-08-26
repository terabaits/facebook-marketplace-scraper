import { db } from '@/lib/db';
import { PostCard } from './post-card';
import { lv } from '@/lib/lv';

export async function MoreFromSection({ postId, categoryId }: { postId: string; categoryId: string | null }) {
  const sameCategory = categoryId
    ? await db.post.findMany({
        where: { status: 'published', deleted_at: null, id: { not: postId }, category_id: categoryId },
        orderBy: { published_at: 'desc' },
        take: 3,
        include: { _count: { select: { comments: true } } }
      })
    : [];
  const filler = sameCategory.length < 3
    ? await db.post.findMany({
        where: { status: 'published', deleted_at: null, id: { notIn: [postId, ...sameCategory.map(p => p.id)] } },
        orderBy: { published_at: 'desc' },
        take: 4 - sameCategory.length,
        include: { _count: { select: { comments: true } } }
      })
    : [];
  const posts = [...sameCategory, ...filler].slice(0, 4);
  if (posts.length === 0) return <p className="text-text-secondary text-sm">Drīzumā vairāk rakstu.</p>;
  return (
    <section className="mt-12 border-t border-border pt-8">
      <h2 className="text-xl font-bold mb-4">{lv.post.moreFrom}</h2>
      <div className="grid grid-cols-4 gap-6">
        {posts.map(p => <PostCard key={p.id} post={p as any} size="small" />)}
      </div>
    </section>
  );
}

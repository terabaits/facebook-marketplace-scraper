import { db } from '@/lib/db';
import { PostCard } from './post-card';

export async function PostGrid({ excludeIds = [], limit = 24, categoryId }: { excludeIds?: string[]; limit?: number; categoryId?: string }) {
  const posts = await db.post.findMany({
    where: {
      status: 'published',
      deleted_at: null,
      id: { notIn: excludeIds },
      ...(categoryId ? { category_id: categoryId } : {})
    },
    orderBy: { published_at: 'desc' },
    take: limit,
    include: { _count: { select: { comments: true } } }
  });
  return (
    <div className="grid grid-cols-12 gap-6">
      {posts.map(p => <PostCard key={p.id} post={p as any} size="small" />)}
    </div>
  );
}

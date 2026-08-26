import { db } from '@/lib/db';
import { PostCard } from '@/components/post-card';
import { AdSlot } from '@/components/ad-slot';

export const revalidate = 60;

export default async function HomePage() {
  const big = await db.post.findMany({
    where: { status: 'published', deleted_at: null, featured_tier: 'big' },
    orderBy: [{ featured_order: 'asc' }, { published_at: 'desc' }],
    take: 2,
    include: { _count: { select: { comments: true } } }
  });
  const medium = await db.post.findMany({
    where: { status: 'published', deleted_at: null, featured_tier: 'medium' },
    orderBy: [{ featured_order: 'asc' }, { published_at: 'desc' }],
    take: 4,
    include: { _count: { select: { comments: true } } }
  });
  const excluded = [...big, ...medium].map(p => p.id);
  const grid = await db.post.findMany({
    where: { status: 'published', deleted_at: null, id: { notIn: excluded } },
    orderBy: { published_at: 'desc' },
    take: 24,
    include: { _count: { select: { comments: true } } }
  });

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* 2 big thumbs */}
      <div className="grid grid-cols-12 gap-6 mb-12">
        {big.map(p => <PostCard key={p.id} post={p as any} size="big" />)}
      </div>

      {/* 4 medium + sticky right-rail ad */}
      <div className="grid grid-cols-12 gap-6 mb-12">
        <div className="col-span-9 grid grid-cols-4 gap-6">
          {medium.map(p => <PostCard key={p.id} post={p as any} size="medium" />)}
        </div>
        <aside className="col-span-3">
          <div className="sticky top-4"><AdSlot slotKey="homepage_right_rail" /></div>
        </aside>
      </div>

      {/* 3-col older grid, no ads */}
      <h2 className="text-xl font-bold mb-4">Visi raksti</h2>
      <div className="grid grid-cols-12 gap-6">
        {grid.map(p => <PostCard key={p.id} post={p as any} size="small" />)}
      </div>
    </div>
  );
}

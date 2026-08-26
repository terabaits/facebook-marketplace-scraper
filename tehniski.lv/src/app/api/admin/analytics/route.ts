import { NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { getSessionOrDevBypass } from '@/lib/auth';

export async function GET() {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const [postsPublished, totalViews, totalComments, pendingComments, searchVolume, adImpressions, adClicks] = await Promise.all([
    db.post.count({ where: { status: 'published' } }),
    db.post.aggregate({ _sum: { view_count: true } }).then(r => r._sum.view_count ?? 0),
    db.comment.count({ where: { status: 'approved' } }),
    db.comment.count({ where: { status: 'pending' } }),
    db.searchQuery.count({ where: { occurred_at: { gte: new Date(Date.now() - 7 * 86400000) } } }),
    db.adEvent.count({ where: { kind: 'impression' } }),
    db.adEvent.count({ where: { kind: 'click' } })
  ]);
  return NextResponse.json({ postsPublished, totalViews, totalComments, pendingComments, searchVolume, adImpressions, adClicks });
}

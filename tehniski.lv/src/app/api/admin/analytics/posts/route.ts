import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { getSessionOrDevBypass } from '@/lib/auth';

export async function GET(req: NextRequest) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const range = new URL(req.url).searchParams.get('range') ?? '7d';
  const days = range === '30d' ? 30 : range === 'all' ? 9999 : 7;
  const since = new Date(Date.now() - days * 86400000);
  const top = await db.$queryRaw<Array<{ id: string; slug: string; title: string; views: number }>>`
    SELECT p.id, p.slug, p.title, COUNT(v.id)::int AS views
    FROM "Post" p
    LEFT JOIN "PostView" v ON v.post_id = p.id AND v.occurred_at >= ${since}
    WHERE p.status = 'published' AND p.deleted_at IS NULL
    GROUP BY p.id
    ORDER BY views DESC
    LIMIT 20
  `;
  return NextResponse.json({ top });
}

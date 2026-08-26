import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { getSessionOrDevBypass } from '@/lib/auth';

export async function GET(req: NextRequest) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { searchParams } = new URL(req.url);
  const sourceId = searchParams.get('source_id');
  const status = searchParams.get('status');
  const where: any = {};
  if (sourceId) where.source_id = sourceId;
  if (status) where.status = status;
  const items = await db.scrapedStory.findMany({
    where, orderBy: { scraped_at: 'desc' }, take: 100,
    include: { source: { select: { name: true } } }
  });
  return NextResponse.json({ items });
}

import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { getSessionOrDevBypass } from '@/lib/auth';

export async function POST(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const { id } = await ctx.params;
  const body = await req.json().catch(() => ({}));
  if (body?.archive) {
    const post = await db.post.update({
      where: { id },
      data: { status: 'archived' }
    });
    return NextResponse.json(post);
  }
  const post = await db.post.update({
    where: { id },
    data: { status: 'published', published_at: new Date() }
  });
  return NextResponse.json(post);
}

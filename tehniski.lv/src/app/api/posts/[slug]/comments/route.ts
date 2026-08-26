import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';

export async function GET(req: NextRequest, ctx: { params: Promise<{ slug: string }> }) {
  const { slug } = await ctx.params;
  const post = await db.post.findUnique({ where: { slug }, select: { id: true } });
  if (!post) return NextResponse.json({ error: 'Not found' }, { status: 404 });
  const top = await db.comment.findMany({
    where: { post_id: post.id, parent_id: null, status: 'approved' },
    orderBy: { created_at: 'asc' },
    take: 50,
    include: {
      replies: { where: { status: 'approved' }, orderBy: { created_at: 'asc' }, take: 5 }
    }
  });
  return NextResponse.json({ comments: top });
}

import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { getSessionOrDevBypass } from '@/lib/auth';
import { z } from 'zod';

const schema = z.object({
  publish_at: z.string().datetime().optional() // if absent, publish now
});

export async function POST(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { id } = await ctx.params;
  const data = schema.parse(await req.json().catch(() => ({})));
  const publishAt = data.publish_at ? new Date(data.publish_at) : new Date();
  const isScheduled = data.publish_at != null;

  const run = await db.newsletterRun.findUnique({
    where: { id },
    include: { selections: { where: { approved: true, post_id: { not: null } } } }
  });
  if (!run) return NextResponse.json({ error: 'Not found' }, { status: 404 });

  const postIds = run.selections.map((s) => s.post_id!).filter(Boolean);
  await db.post.updateMany({
    where: { id: { in: postIds } },
    data: {
      status: isScheduled ? 'scheduled' : 'published',
      publish_at: isScheduled ? publishAt : null,
      published_at: isScheduled ? null : publishAt
    }
  });
  await db.newsletterRun.update({
    where: { id },
    data: {
      status: isScheduled ? 'writing' : 'published',
      completed_at: isScheduled ? null : new Date()
    }
  });

  // Auto-fill the first post's excerpt with the intro if not already set
  if (!isScheduled && run.editor_feedback) {
    const firstPost = await db.post.findFirst({ where: { id: { in: postIds } }, orderBy: { created_at: 'asc' } });
    if (firstPost && !firstPost.excerpt) {
      await db.post.update({ where: { id: firstPost.id }, data: { excerpt: run.editor_feedback } });
    }
  }

  return NextResponse.json({ ok: true, published: postIds.length });
}

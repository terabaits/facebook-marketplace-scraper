import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { TokenBucket } from '@/lib/rate-limit';
import { createHash } from 'node:crypto';
import { z } from 'zod';

const commentBucket = new TokenBucket(5, 60_000);

const schema = z.object({
  post_id: z.string(),
  parent_id: z.string().nullable().optional(),
  author_name: z.string().min(1).max(80),
  author_email: z.string().email().max(200),
  body: z.string().min(1).max(5000)
});

export async function POST(req: NextRequest) {
  const ip = req.headers.get('x-forwarded-for') ?? '0.0.0.0';
  if (!commentBucket.tryConsume(ip)) return NextResponse.json({ error: 'Pārāk daudz pieprasījumu' }, { status: 429 });
  const data = schema.parse(await req.json());
  const post = await db.post.findUnique({ where: { id: data.post_id }, select: { id: true } });
  if (!post) return NextResponse.json({ error: 'Post not found' }, { status: 404 });
  const depth = data.parent_id
    ? (await db.comment.findUnique({ where: { id: data.parent_id }, select: { depth: true } }))?.depth ?? 0
    : 0;
  const emailHash = createHash('sha256').update(data.author_email).digest('hex');

  const comment = await db.$transaction(async (tx) => {
    const c = await tx.comment.create({
      data: {
        post_id: data.post_id, parent_id: data.parent_id ?? null, depth,
        author_name: data.author_name, author_email_hash: emailHash,
        body: data.body, status: 'pending', is_author: false
      }
    });
    if (data.parent_id) {
      await tx.comment.update({
        where: { id: data.parent_id },
        data: { reply_count: { increment: 1 }, last_reply_at: new Date() }
      });
    }
    return c;
  });
  return NextResponse.json({ id: comment.id, status: 'pending' });
}

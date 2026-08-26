import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { getSessionOrDevBypass } from '@/lib/auth';
import { z } from 'zod';

const schema = z.object({
  post_id: z.string(),
  parent_id: z.string().nullable().optional(),
  body: z.string().min(1).max(5000),
  is_author: z.boolean().default(true)
});

export async function POST(req: NextRequest) {
  const session = await getSessionOrDevBypass();
  if (!session?.user?.email) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const author = await db.author.findFirst({ where: { is_admin: true } });
  if (!author) return NextResponse.json({ error: 'No admin author' }, { status: 400 });
  const data = schema.parse(await req.json());
  const depth = data.parent_id
    ? (await db.comment.findUnique({ where: { id: data.parent_id }, select: { depth: true } }))?.depth ?? 0
    : 0;
  const comment = await db.$transaction(async (tx) => {
    const c = await tx.comment.create({
      data: {
        post_id: data.post_id, parent_id: data.parent_id ?? null, depth,
        author_id: author.id, author_name: author.name, author_email_hash: '',
        body: data.body, status: 'approved', is_author: data.is_author
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
  return NextResponse.json(comment);
}

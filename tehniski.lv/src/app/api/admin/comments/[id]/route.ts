import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { getSessionOrDevBypass } from '@/lib/auth';
import { z } from 'zod';

const patchSchema = z.object({
  status: z.enum(['approved', 'pending', 'spam', 'deleted']).optional(),
  body: z.string().min(1).max(5000).optional()
});

export async function PATCH(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const session = await getSessionOrDevBypass();
  if (!session?.user?.email) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { id } = await ctx.params;
  const data = patchSchema.parse(await req.json());
  const comment = await db.comment.update({ where: { id }, data });
  return NextResponse.json(comment);
}

export async function DELETE(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const session = await getSessionOrDevBypass();
  if (!session?.user?.email) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { id } = await ctx.params;
  await db.comment.update({ where: { id }, data: { status: 'deleted' } });
  return NextResponse.json({ ok: true });
}

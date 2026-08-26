import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { getSessionOrDevBypass } from '@/lib/auth';
import { z } from 'zod';

const patchSchema = z.object({
  name: z.string().min(1).optional(),
  feed_url: z.string().url().optional(),
  site_url: z.string().url().optional(),
  active: z.boolean().optional(),
  parser_config: z.object({ kind: z.enum(['readability', 'playwright']) }).optional()
});

export async function PATCH(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { id } = await ctx.params;
  const data = patchSchema.parse(await req.json());
  const source = await db.rssSource.update({ where: { id }, data });
  return NextResponse.json(source);
}

export async function DELETE(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { id } = await ctx.params;
  await db.rssSource.delete({ where: { id } });
  return NextResponse.json({ ok: true });
}

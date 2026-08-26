import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { getSessionOrDevBypass } from '@/lib/auth';
import { z } from 'zod';

const schema = z.object({ name: z.string().min(1).optional(), width: z.number().int().positive().optional(), height: z.number().int().positive().optional(), active: z.boolean().optional() });

export async function PATCH(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { id } = await ctx.params;
  const data = schema.parse(await req.json());
  const slot = await db.adSlot.update({ where: { id }, data });
  return NextResponse.json(slot);
}

export async function DELETE(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { id } = await ctx.params;
  await db.adSlot.delete({ where: { id } });
  return NextResponse.json({ ok: true });
}

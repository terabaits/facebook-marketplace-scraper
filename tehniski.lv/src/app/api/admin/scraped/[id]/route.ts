import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { getSessionOrDevBypass } from '@/lib/auth';
import { z } from 'zod';

const schema = z.object({ status: z.enum(['new', 'used', 'ignored', 'failed']) });

export async function PATCH(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { id } = await ctx.params;
  const { status } = schema.parse(await req.json());
  const item = await db.scrapedStory.update({ where: { id }, data: { status } });
  return NextResponse.json(item);
}

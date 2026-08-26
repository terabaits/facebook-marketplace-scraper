import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { getSessionOrDevBypass } from '@/lib/auth';
import { z } from 'zod';

const patchSchema = z.object({
  selected_subject: z.string().min(1).optional()
});

export async function GET(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { id } = await ctx.params;
  const run = await db.newsletterRun.findUnique({
    where: { id },
    include: {
      selections: {
        orderBy: { rank: 'asc' },
        include: { scraped_story: { include: { source: { select: { name: true } } } }, post: true }
      },
      posts: true,
      previous_run: { select: { id: true, target_date: true } }
    }
  });
  if (!run) return NextResponse.json({ error: 'Not found' }, { status: 404 });
  return NextResponse.json(run);
}

export async function PATCH(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { id } = await ctx.params;
  const data = patchSchema.parse(await req.json());
  const run = await db.newsletterRun.update({ where: { id }, data });
  return NextResponse.json(run);
}

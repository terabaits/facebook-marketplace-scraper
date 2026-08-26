import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { getSessionOrDevBypass } from '@/lib/auth';

export async function POST(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { id } = await ctx.params;

  const prompt = await db.promptTemplate.findUnique({ where: { id } });
  if (!prompt) return NextResponse.json({ error: 'Not found' }, { status: 404 });

  await db.$transaction([
    db.promptTemplate.updateMany({
      where: { key: prompt.key, active: true },
      data: { active: false }
    }),
    db.promptTemplate.update({
      where: { id },
      data: { active: true }
    })
  ]);
  return NextResponse.json({ ok: true });
}

import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { getSessionOrDevBypass } from '@/lib/auth';

export async function POST(req: NextRequest, ctx: { params: Promise<{ id: string; selectionId: string }> }) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { selectionId } = await ctx.params;
  const sel = await db.storySelection.update({
    where: { id: selectionId },
    data: { approved: true }
  });
  return NextResponse.json(sel);
}

export async function DELETE(req: NextRequest, ctx: { params: Promise<{ id: string; selectionId: string }> }) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { selectionId } = await ctx.params;
  const sel = await db.storySelection.update({
    where: { id: selectionId },
    data: { approved: false }
  });
  return NextResponse.json(sel);
}

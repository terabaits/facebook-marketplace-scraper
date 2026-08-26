import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { getSessionOrDevBypass } from '@/lib/auth';
import { buildPacket } from '@/lib/editorial/packet-builder';
import type { StepName } from '@/lib/editorial/schemas';

export async function GET(req: NextRequest, ctx: { params: Promise<{ id: string; step: string }> }) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { id, step } = await ctx.params;
  if (!['pick-stories', 'pick-subject', 'write'].includes(step)) {
    return NextResponse.json({ error: 'Invalid step' }, { status: 400 });
  }
  const url = new URL(req.url);
  const selectionId = url.searchParams.get('selection_id') ?? undefined;

  const run = await db.newsletterRun.findUnique({ where: { id } });
  if (!run) return NextResponse.json({ error: 'Not found' }, { status: 404 });

  const packet = await buildPacket(step as StepName, { runId: id, feedback: run.editor_feedback ?? undefined }, selectionId);
  return new NextResponse(packet, { headers: { 'Content-Type': 'text/markdown; charset=utf-8' } });
}

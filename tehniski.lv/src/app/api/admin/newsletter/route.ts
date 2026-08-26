import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';
import { db } from '@/lib/db';
import { getSessionOrDevBypass } from '@/lib/auth';

const startSchema = z.object({
  target_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Must be YYYY-MM-DD'),
  previous_run_text: z.string().optional() // pasted from previous newsletter for dedup
});

export async function GET() {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const runs = await db.newsletterRun.findMany({
    orderBy: { target_date: 'desc' },
    take: 30,
    include: { _count: { select: { selections: true, posts: true } } }
  });
  return NextResponse.json({ runs });
}

export async function POST(req: NextRequest) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const data = startSchema.parse(await req.json());
  const targetDate = new Date(`${data.target_date}T00:00:00.000Z`);

  // Find the most recent previous run (by target_date desc, before targetDate)
  const previous = await db.newsletterRun.findFirst({
    where: { target_date: { lt: targetDate } },
    orderBy: { target_date: 'desc' }
  });

  // Fails if target_date already has a run
  const existing = await db.newsletterRun.findUnique({ where: { target_date: targetDate } });
  if (existing) return NextResponse.json({ error: 'Run already exists for this date' }, { status: 400 });

  const run = await db.newsletterRun.create({
    data: {
      target_date: targetDate,
      previous_run_id: previous?.id ?? null,
      status: 'awaiting_editor',
      editor_feedback: data.previous_run_text ?? null
    }
  });
  return NextResponse.json(run);
}

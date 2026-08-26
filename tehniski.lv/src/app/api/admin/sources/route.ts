import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { getSessionOrDevBypass } from '@/lib/auth';
import { z } from 'zod';

const schema = z.object({
  name: z.string().min(1),
  feed_url: z.string().url(),
  site_url: z.string().url(),
  active: z.boolean().default(true),
  parser_config: z
    .object({ kind: z.enum(['readability', 'playwright']) })
    .default({ kind: 'readability' })
});

export async function POST(req: NextRequest) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const data = schema.parse(await req.json());
  const source = await db.rssSource.create({ data });
  return NextResponse.json(source);
}

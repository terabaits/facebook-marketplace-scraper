import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { getSessionOrDevBypass } from '@/lib/auth';
import { z } from 'zod';

const schema = z.object({ key: z.string().min(1), name: z.string().min(1), width: z.number().int().positive(), height: z.number().int().positive(), active: z.boolean().default(true) });

export async function POST(req: NextRequest) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const data = schema.parse(await req.json());
  const slot = await db.adSlot.create({ data });
  return NextResponse.json(slot);
}

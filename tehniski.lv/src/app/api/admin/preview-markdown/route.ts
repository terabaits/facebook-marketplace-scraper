import { NextRequest, NextResponse } from 'next/server';
import { renderMarkdown } from '@/lib/markdown';
import { getSessionOrDevBypass } from '@/lib/auth';
import { z } from 'zod';

const schema = z.object({ md: z.string().max(200_000) });

export async function POST(req: NextRequest) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { md } = schema.parse(await req.json());
  return NextResponse.json({ html: renderMarkdown(md) });
}

import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { getSessionOrDevBypass } from '@/lib/auth';
import { z } from 'zod';

const schema = z.object({ publish_at: z.string().datetime() });

export async function POST(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const { id } = await ctx.params;
  const { publish_at } = schema.parse(await req.json());
  const post = await db.post.update({
    where: { id },
    data: { status: 'scheduled', publish_at: new Date(publish_at) }
  });
  return NextResponse.json(post);
}

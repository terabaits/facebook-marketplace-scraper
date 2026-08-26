import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { getSessionOrDevBypass } from '@/lib/auth';
import { z } from 'zod';

const schema = z.object({
  featured_tier: z.enum(['big', 'medium']).nullable(),
  featured_order: z.number().int().nullable().optional()
});

export async function POST(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const { id } = await ctx.params;
  const data = schema.parse(await req.json());
  const post = await db.post.update({
    where: { id },
    data: {
      featured_tier: data.featured_tier,
      featured_order: data.featured_order ?? null,
      featured_at: data.featured_tier ? new Date() : null
    }
  });
  return NextResponse.json(post);
}

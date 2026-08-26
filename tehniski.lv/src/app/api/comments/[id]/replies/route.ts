import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { z } from 'zod';

const schema = z.object({ offset: z.coerce.number().int().min(0).default(0), limit: z.coerce.number().int().min(1).max(50).default(20) });

export async function GET(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const { searchParams } = new URL(req.url);
  const { offset, limit } = schema.parse({ offset: searchParams.get('offset') ?? 0, limit: searchParams.get('limit') ?? 20 });
  const replies = await db.comment.findMany({
    where: { parent_id: id, status: 'approved' },
    orderBy: { created_at: 'asc' },
    skip: offset, take: limit
  });
  return NextResponse.json({ replies });
}

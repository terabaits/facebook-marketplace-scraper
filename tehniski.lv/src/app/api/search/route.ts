import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { z } from 'zod';
import { createHash } from 'node:crypto';

const querySchema = z.object({
  q: z.string().min(1).max(200),
  limit: z.coerce.number().int().min(1).max(20).default(10)
});

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const parsed = querySchema.safeParse({ q: searchParams.get('q'), limit: searchParams.get('limit') ?? 10 });
  if (!parsed.success) return NextResponse.json({ error: 'Invalid query' }, { status: 400 });
  const { q, limit } = parsed.data;
  const ipHash = createHash('sha256').update(req.headers.get('x-forwarded-for') ?? '0.0.0.0').digest('hex').slice(0, 32);
  try {
    const results = await db.$queryRaw<Array<{ id: string; slug: string; title: string; excerpt: string; rank: number }>>`
      SELECT id, slug, title, excerpt,
        ts_rank(search_vector, plainto_tsquery('latvian', ${q})) AS rank
      FROM "Post"
      WHERE status = 'published' AND deleted_at IS NULL
        AND search_vector @@ plainto_tsquery('latvian', ${q})
      ORDER BY rank DESC, published_at DESC
      LIMIT ${limit}
    `;
    await db.searchQuery.create({ data: { query: q, result_count: results.length, ip_hash: ipHash } });
    return NextResponse.json({ results });
  } catch (e) {
    return NextResponse.json({ results: [], error: String(e) }, { status: 200 });
  }
}

import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { getSessionOrDevBypass } from '@/lib/auth';
import { z } from 'zod';

const schema = z.object({
  slot_id: z.string(),
  kind: z.enum(['image', 'embed']),
  image_url: z.string().nullable().optional(),
  target_url: z.string().nullable().optional(),
  alt_text: z.string().nullable().optional(),
  embed_html: z.string().nullable().optional(),
  weight: z.number().int().min(1).default(1),
  active: z.boolean().default(true),
  starts_at: z.string().nullable().optional(),
  ends_at: z.string().nullable().optional()
});

export async function POST(req: NextRequest) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const data = schema.parse(await req.json());
  const creative = await db.adCreative.create({
    data: {
      slot_id: data.slot_id, kind: data.kind,
      image_url: data.image_url ?? null, target_url: data.target_url ?? null, alt_text: data.alt_text ?? null,
      embed_html: data.embed_html ?? null,
      weight: data.weight, active: data.active,
      starts_at: data.starts_at ? new Date(data.starts_at) : null,
      ends_at: data.ends_at ? new Date(data.ends_at) : null
    }
  });
  return NextResponse.json(creative);
}

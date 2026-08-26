import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { getSessionOrDevBypass } from '@/lib/auth';
import { z } from 'zod';

const schema = z.object({
  image_url: z.string().nullable().optional(),
  target_url: z.string().nullable().optional(),
  alt_text: z.string().nullable().optional(),
  embed_html: z.string().nullable().optional(),
  weight: z.number().int().min(1).optional(),
  active: z.boolean().optional(),
  starts_at: z.string().nullable().optional(),
  ends_at: z.string().nullable().optional()
});

export async function PATCH(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { id } = await ctx.params;
  const data = schema.parse(await req.json());
  const creative = await db.adCreative.update({
    where: { id },
    data: {
      ...data,
      starts_at: data.starts_at ? new Date(data.starts_at) : (data.starts_at === null ? null : undefined),
      ends_at: data.ends_at ? new Date(data.ends_at) : (data.ends_at === null ? null : undefined)
    }
  });
  return NextResponse.json(creative);
}

export async function DELETE(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { id } = await ctx.params;
  await db.adCreative.delete({ where: { id } });
  return NextResponse.json({ ok: true });
}

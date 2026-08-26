import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { getSessionOrDevBypass } from '@/lib/auth';
import { z } from 'zod';
import { renderMarkdown } from '@/lib/markdown';

const updateSchema = z.object({
  title: z.string().min(1).optional(),
  excerpt: z.string().min(1).optional(),
  content_md: z.string().min(1).optional(),
  cover_image_url: z.string().nullable().optional(),
  cover_image_alt: z.string().nullable().optional(),
  category_id: z.string().nullable().optional(),
  featured_tier: z.enum(['big', 'medium']).nullable().optional()
});

export async function PATCH(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const { id } = await ctx.params;
  const data = updateSchema.parse(await req.json());
  const content_html = data.content_md ? renderMarkdown(data.content_md) : undefined;

  const post = await db.post.update({
    where: { id },
    data: {
      ...data,
      ...(content_html ? { content_html } : {}),
      featured_at: data.featured_tier ? new Date() : null
    }
  });
  return NextResponse.json(post);
}

export async function DELETE(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const { id } = await ctx.params;
  await db.post.update({ where: { id }, data: { deleted_at: new Date() } });
  return NextResponse.json({ ok: true });
}

import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { getSessionOrDevBypass } from '@/lib/auth';
import { z } from 'zod';
import { slugify } from '@/lib/slug';
import { renderMarkdown } from '@/lib/markdown';

const postSchema = z.object({
  title: z.string().min(1),
  excerpt: z.string().min(1),
  content_md: z.string().min(1),
  cover_image_url: z.string().nullable().optional(),
  cover_image_alt: z.string().nullable().optional(),
  category_id: z.string().nullable().optional(),
  featured_tier: z.enum(['big', 'medium']).nullable().optional()
});

export async function POST(req: NextRequest) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const data = postSchema.parse(await req.json());
  const author = await db.author.findFirst();
  if (!author) return NextResponse.json({ error: 'No author in DB' }, { status: 400 });

  const baseSlug = slugify(data.title) || 'post';
  const slug = `${baseSlug}-${Date.now().toString(36).slice(-4)}`;

  const post = await db.post.create({
    data: {
      title: data.title,
      slug,
      excerpt: data.excerpt,
      content_md: data.content_md,
      content_html: renderMarkdown(data.content_md),
      cover_image_url: data.cover_image_url ?? null,
      cover_image_alt: data.cover_image_alt ?? null,
      category_id: data.category_id ?? null,
      featured_tier: data.featured_tier ?? null,
      featured_at: data.featured_tier ? new Date() : null,
      author_id: author.id,
      status: 'draft',
      source: 'manual',
      language: 'lv'
    }
  });
  return NextResponse.json(post);
}

import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { getSessionOrDevBypass } from '@/lib/auth';
import { z } from 'zod';

const schema = z.object({
  site_name: z.string().optional(),
  default_og_image_url: z.string().url().optional(),
  footer_markdown: z.string().optional(),
  contact_email: z.string().email().optional(),
  social_twitter: z.string().optional(),
  social_facebook: z.string().optional(),
  social_linkedin: z.string().optional()
});

export async function PATCH(req: NextRequest) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const data = schema.parse(await req.json());
  await db.$transaction(Object.entries(data).filter(([_, v]) => v !== undefined).map(([key, value]) =>
    db.setting.upsert({ where: { key }, update: { value: String(value) }, create: { key, value: String(value) } })
  ));
  return NextResponse.json({ ok: true });
}

import { NextRequest, NextResponse } from 'next/server';
import { recordPostView } from '@/lib/analytics';

export async function POST(req: NextRequest) {
  const { post_id } = await req.json();
  if (!post_id) return NextResponse.json({ error: 'post_id required' }, { status: 400 });
  const ip = req.headers.get('x-forwarded-for') ?? '0.0.0.0';
  const ua = req.headers.get('user-agent') ?? '';
  const referer = req.headers.get('referer') ?? undefined;
  await recordPostView(post_id, ip, ua, referer);
  return NextResponse.json({ ok: true });
}

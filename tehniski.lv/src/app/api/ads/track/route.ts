import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { createHash } from 'node:crypto';

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const creativeId = searchParams.get('creative_id');
  const kind = searchParams.get('kind');
  const redirect = searchParams.get('redirect');
  if (!creativeId || (kind !== 'impression' && kind !== 'click')) {
    return NextResponse.json({ error: 'Bad params' }, { status: 400 });
  }
  const ip = req.headers.get('x-forwarded-for') ?? '0.0.0.0';
  const ua = req.headers.get('user-agent') ?? '';
  const ipHash = createHash('sha256').update(ip).digest('hex').slice(0, 32);
  await db.adEvent.create({ data: { creative_id: creativeId, kind, ip_hash: ipHash, user_agent: ua.slice(0, 256) } });
  if (kind === 'click') await db.adCreative.update({ where: { id: creativeId }, data: { clicks: { increment: 1 } } });
  if (kind === 'click' && redirect) return NextResponse.redirect(redirect);
  return NextResponse.json({ ok: true });
}

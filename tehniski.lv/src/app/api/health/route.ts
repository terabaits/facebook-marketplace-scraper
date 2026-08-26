import { NextResponse } from 'next/server';
import { db } from '@/lib/db';

export async function GET() {
  const dbOk = await db.$queryRaw`SELECT 1`.then(() => true).catch(() => false);
  const heartbeat = await db.workerHeartbeat.findUnique({ where: { id: 'singleton' } }).catch(() => null);
  const heartbeatAge = heartbeat ? Math.floor((Date.now() - heartbeat.last_seen.getTime()) / 1000) : null;
  const version = '0.2.0';
  return NextResponse.json({ ok: dbOk, db: dbOk ? 'up' : 'down', worker_heartbeat_age_seconds: heartbeatAge, version });
}

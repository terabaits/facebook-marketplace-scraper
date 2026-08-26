import { db } from '@/lib/db';
import { createHash } from 'node:crypto';

const dedup = new Map<string, number>();
const DEDUP_MS = 30 * 60 * 1000;

export async function recordPostView(postId: string, ip: string, userAgent: string, referer?: string) {
  const ipHash = createHash('sha256').update(ip).digest('hex').slice(0, 32);
  const key = `${postId}:${ipHash}`;
  const now = Date.now();
  const last = dedup.get(key);
  if (last && now - last < DEDUP_MS) return;
  dedup.set(key, now);
  if (dedup.size > 10000) {
    for (const [k, v] of dedup) if (now - v > DEDUP_MS) dedup.delete(k);
  }
  await db.$transaction([
    db.postView.create({ data: { post_id: postId, ip_hash: ipHash, user_agent: userAgent.slice(0, 256), referer: referer?.slice(0, 500) } }),
    db.post.update({ where: { id: postId }, data: { view_count: { increment: 1 } } })
  ]);
}

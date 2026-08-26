import cron from 'node-cron';
import { db } from '../lib/db.js';
import { log } from '../lib/logger.js';

export async function publishDuePosts() {
  const now = new Date();
  // Partial index on (publish_at) WHERE status='scheduled' makes this fast (migration 0003)
  const due = await db.post.findMany({
    where: { status: 'scheduled', publish_at: { lte: now } },
    select: { id: true, title: true, publish_at: true }
  });
  for (const post of due) {
    try {
      await db.post.update({ where: { id: post.id }, data: { status: 'published', published_at: post.publish_at ?? now } });
      log.info('[publish-scheduled] published', { id: post.id, title: post.title });
    } catch (e: any) {
      log.error('[publish-scheduled] error', { id: post.id, error: e.message });
    }
  }
  if (due.length === 0) log.info('[publish-scheduled] tick (none due)');
  return due.length;
}

export function startPublishScheduled() {
  return cron.schedule('* * * * *', () => {
    publishDuePosts().catch((e) => log.error('[publish-scheduled] cron error', { error: e.message }));
  });
}

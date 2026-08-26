import cron from 'node-cron';
import { db } from '../lib/db.js';

export function startHeartbeat() {
  return cron.schedule('* * * * *', async () => {  // every minute
    try {
      await db.workerHeartbeat.upsert({
        where: { id: 'singleton' },
        update: { last_seen: new Date(), version: '0.2.0' },
        create: { id: 'singleton', last_seen: new Date(), version: '0.2.0', started_at: new Date() }
      });
    } catch (e) {
      console.error('[heartbeat] failed:', e);
    }
  });
}

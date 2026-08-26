import { log } from './lib/logger.js';
import { db } from './lib/db.js';
import { startHeartbeat } from './jobs/heartbeat.js';
import { startFetchRss } from './jobs/fetch-rss.js';
import { startPublishScheduled } from './jobs/publish-scheduled.js';

log.info('[worker] starting', { pid: process.pid, node: process.version });

const heartbeat = startHeartbeat();
const fetchRss = startFetchRss();
const publishScheduled = startPublishScheduled();

async function shutdown(signal: string) {
  log.info(`[worker] received ${signal}, shutting down`);
  heartbeat.stop(); fetchRss.stop(); publishScheduled.stop();
  await db.$disconnect();
  process.exit(0);
}
process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));

log.info('[worker] all jobs scheduled, running');

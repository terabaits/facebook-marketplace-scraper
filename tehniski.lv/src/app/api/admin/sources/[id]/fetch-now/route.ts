import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { getSessionOrDevBypass } from '@/lib/auth';

// M2 Task 5 plan deviation (documented in m2-task-5-report.md):
// The plan called for importing `fetchAndScrapeSource` from `@/worker/jobs/fetch-rss`
// and invoking it inline. That path is not available because:
//   1. `@/...` only resolves to `./src/*` per tsconfig (the worker dir is outside `src`).
//   2. `fetchAndScrapeSource` in `worker/jobs/fetch-rss.ts` is not exported.
//   3. Worker modules use `.js` extension imports for tsx/ESM compatibility which
//      don't resolve cleanly under the Next.js bundler.
// We fall back to the documented alternative: mark the request with `last_error =
// 'FETCH_REQUESTED'` so the operator can see it in the admin UI, and let the next
// 3h cron tick (worker `startFetchRss`) pick it up. A future task can add a real
// `worker_jobs` queue + a `route.ts` that pokes the worker process directly.
export async function POST(req: NextRequest, ctx: { params: Promise<{ id: string }> }) {
  const session = await getSessionOrDevBypass();
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  const { id } = await ctx.params;
  const source = await db.rssSource.findUnique({ where: { id } });
  if (!source) return NextResponse.json({ error: 'Not found' }, { status: 404 });
  if (!source.active) {
    return NextResponse.json({ error: 'Source is inactive' }, { status: 400 });
  }
  await db.rssSource.update({
    where: { id },
    data: { last_error: 'FETCH_REQUESTED' }
  });
  return NextResponse.json({
    ok: true,
    message:
      'Pieprasījums atzīmēts. Nākamais 3h cron cikls to paņems; lai scrāpētu uzreiz, palaidiet `npm run worker` atsevišķi.'
  });
}

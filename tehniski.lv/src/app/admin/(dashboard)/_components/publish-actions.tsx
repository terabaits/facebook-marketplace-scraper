'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

export function PublishActions({ post }: { post: any }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [scheduleAt, setScheduleAt] = useState('');
  const [featureTier, setFeatureTier] = useState<string>(post?.featured_tier ?? '');

  async function call(path: string, body?: any) {
    setBusy(true);
    try {
      await fetch(`/api/admin/posts/${post.id}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: body ? JSON.stringify(body) : undefined
      });
    } finally {
      setBusy(false);
    }
    router.refresh();
  }

  return (
    <div className="flex flex-wrap gap-2 mb-6 items-center">
      {post.status !== 'published' && (
        <button
          onClick={() => call('/publish')}
          disabled={busy}
          className="bg-success text-bg-base px-3 py-1 rounded text-sm font-bold disabled:opacity-50"
        >
          Publicēt
        </button>
      )}
      {post.status !== 'archived' && (
        <button
          onClick={() => call('/publish', { archive: true })}
          disabled={busy}
          className="bg-bg-subtle px-3 py-1 rounded text-sm disabled:opacity-50"
        >
          Arhivēt
        </button>
      )}
      <div className="flex gap-2 items-center ml-4">
        <input
          type="datetime-local"
          value={scheduleAt}
          onChange={(e) => setScheduleAt(e.target.value)}
          className="bg-bg-elevated border border-border rounded px-2 py-1 text-sm"
        />
        <button
          onClick={() =>
            scheduleAt && call('/schedule', { publish_at: new Date(scheduleAt).toISOString() })
          }
          disabled={busy || !scheduleAt}
          className="bg-warning text-bg-base px-3 py-1 rounded text-sm font-bold disabled:opacity-50"
        >
          Plānot
        </button>
      </div>
      <div className="flex gap-2 items-center ml-4">
        <select
          value={featureTier}
          onChange={(e) => setFeatureTier(e.target.value)}
          className="bg-bg-elevated border border-border rounded px-2 py-1 text-sm"
        >
          <option value="">Nav izcelts</option>
          <option value="big">Lielais</option>
          <option value="medium">Vidējais</option>
        </select>
        <button
          onClick={() => call('/feature', { featured_tier: featureTier || null })}
          disabled={busy}
          className="bg-accent-primary text-bg-base px-3 py-1 rounded text-sm font-bold disabled:opacity-50"
        >
          Saglabāt izcelšanu
        </button>
      </div>
    </div>
  );
}

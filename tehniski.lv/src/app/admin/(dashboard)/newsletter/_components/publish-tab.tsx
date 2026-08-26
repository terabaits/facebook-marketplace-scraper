'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

type Selection = {
  id: string;
  approved: boolean;
  post_id: string | null;
  post: { id: string; title: string; slug: string; status: string } | null;
};

type Post = { id: string; title: string; status: string; slug: string; published_at: Date | null; publish_at: Date | null };

type Run = {
  id: string;
  status: string;
  subject_main: string | null;
  selected_subject: string | null;
  editor_feedback: string | null;
  selections: Selection[];
  posts: Post[];
};

export function PublishTab({ run }: { run: Run }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scheduleAt, setScheduleAt] = useState('');
  const [success, setSuccess] = useState<string | null>(null);

  const approvedWithPosts = run.selections.filter((s) => s.approved && s.post_id);
  const readyCount = approvedWithPosts.length;

  async function publishNow() {
    setBusy(true);
    setError(null);
    setSuccess(null);
    const res = await fetch(`/api/admin/newsletter/${run.id}/publish`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    if (res.ok) {
      const data = await res.json();
      setSuccess(`Publicēts ${data.published} raksti`);
      router.refresh();
    } else {
      const e = await res.json().catch(() => ({}));
      setError(e.error ?? 'Kļūda');
    }
    setBusy(false);
  }

  async function schedule() {
    if (!scheduleAt) {
      setError('Norādi publicēšanas laiku');
      return;
    }
    setBusy(true);
    setError(null);
    setSuccess(null);
    const res = await fetch(`/api/admin/newsletter/${run.id}/publish`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ publish_at: new Date(scheduleAt).toISOString() })
    });
    if (res.ok) {
      const data = await res.json();
      setSuccess(`Ieplānots ${data.published} raksti`);
      router.refresh();
    } else {
      const e = await res.json().catch(() => ({}));
      setError(e.error ?? 'Kļūda');
    }
    setBusy(false);
  }

  return (
    <div>
      <h2 className="text-lg font-bold mb-4">Publicēšana</h2>

      <div className="bg-bg-elevated border border-border rounded-md p-4 mb-4">
        <p className="text-sm mb-1">
          Temats: <span className="font-bold">{run.selected_subject ?? run.subject_main ?? '—'}</span>
        </p>
        {run.editor_feedback && (
          <p className="text-sm text-text-secondary mt-2">
            <span className="font-mono text-xs">Intro: </span>
            {run.editor_feedback}
          </p>
        )}
        <p className="text-xs text-text-secondary font-mono mt-2">
          {readyCount} raksti gatavi publicēšanai · statuss: {run.status}
        </p>
      </div>

      {readyCount === 0 ? (
        <p className="text-text-secondary text-sm">
          Nav gatavu rakstu publicēšanai. Vispirms uzraksti vismaz vienu rakstu (cilnē "Rakstīšana").
        </p>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <button
              onClick={publishNow}
              disabled={busy}
              className="bg-accent-primary text-bg-base font-bold px-4 py-2 rounded disabled:opacity-50"
            >
              {busy ? 'Publicē…' : `Publicēt tagad (${readyCount})`}
            </button>
          </div>
          <div className="flex items-end gap-3">
            <label className="block text-sm">
              Publicēšanas laiks
              <input
                type="datetime-local"
                value={scheduleAt}
                onChange={(e) => setScheduleAt(e.target.value)}
                className="mt-1 bg-bg-elevated border border-border rounded-md px-3 py-2 font-mono text-sm"
              />
            </label>
            <button
              onClick={schedule}
              disabled={busy}
              className="bg-bg-subtle px-3 py-2 rounded text-sm disabled:opacity-50"
            >
              {busy ? 'Plāno…' : 'Ieplānot'}
            </button>
          </div>
          {error && <p className="text-sm text-danger">{error}</p>}
          {success && <p className="text-sm text-success">{success}</p>}
        </div>
      )}

      {run.posts.length > 0 && (
        <div className="mt-6">
          <h3 className="font-bold mb-2">Šī izdevuma raksti</h3>
          <ul className="text-sm space-y-1">
            {run.posts.map((p) => (
              <li key={p.id} className="font-mono">
                {p.title} · {p.status}
                {p.published_at && ` · publicēts ${new Date(p.published_at).toLocaleString('lv-LV')}`}
                {p.publish_at && !p.published_at && ` · ieplānots ${new Date(p.publish_at).toLocaleString('lv-LV')}`}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

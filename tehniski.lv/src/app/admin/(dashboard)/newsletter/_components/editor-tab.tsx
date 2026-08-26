'use client';
import { useState } from 'react';
import { PrepareTaskModal } from './prepare-task-modal';
import { useRouter } from 'next/navigation';

type Selection = {
  id: string;
  rank: number;
  approved: boolean;
  notes: string | null;
  scraped_story: { id: string; title: string; url: string; source: { name: string } };
};

type Run = {
  id: string;
  status: string;
  selections: Selection[];
  editor_feedback: string | null;
};

export function EditorTab({ run }: { run: Run }) {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const candidates = run.selections ?? [];

  async function approve(id: string) {
    await fetch(`/api/admin/newsletter/${run.id}/selections/${id}/approve`, { method: 'POST' });
    router.refresh();
  }
  async function skip(id: string) {
    await fetch(`/api/admin/newsletter/${run.id}/selections/${id}/approve`, { method: 'DELETE' });
    router.refresh();
  }

  const approvedCount = candidates.filter((c) => c.approved).length;

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <div>
          <h2 className="text-lg font-bold">Stāstu izvēle</h2>
          <p className="text-xs text-text-secondary font-mono">
            {approvedCount} apstiprināts no {candidates.length} kandidātiem
          </p>
        </div>
        <button
          onClick={() => setOpen(true)}
          className="bg-accent-primary text-bg-base font-bold px-4 py-2 rounded"
        >
          Sagatavot uzdevumu
        </button>
      </div>

      {run.editor_feedback && (
        <div className="bg-bg-elevated border border-border rounded-md p-3 mb-4 text-sm">
          <p className="text-xs text-text-secondary font-mono mb-1">Mavis ievadruna (tiks izmantota kā intro):</p>
          <p>{run.editor_feedback}</p>
        </div>
      )}

      {candidates.length === 0 ? (
        <p className="text-text-secondary text-sm">
          Nav kandidātu. Palaid uzdevumu, lai saņemtu Mavis izvēli.
        </p>
      ) : (
        <div className="space-y-2">
          {candidates.map((c) => (
            <div
              key={c.id}
              className={`bg-bg-elevated border rounded-md p-3 ${
                c.approved ? 'border-success' : 'border-border'
              }`}
            >
              <div className="flex justify-between">
                <div>
                  <div className="font-bold">
                    #{c.rank} {c.scraped_story.title}
                  </div>
                  <div className="text-xs text-text-secondary font-mono">
                    {c.scraped_story.source.name} · {c.scraped_story.url}
                  </div>
                  {c.notes && <p className="text-sm mt-1">{c.notes}</p>}
                </div>
                <div className="flex gap-2 shrink-0">
                  <button
                    onClick={() => approve(c.id)}
                    disabled={c.approved}
                    className={
                      c.approved
                        ? 'bg-success text-bg-base px-3 py-1 rounded text-sm'
                        : 'bg-bg-subtle px-3 py-1 rounded text-sm'
                    }
                  >
                    {c.approved ? 'Apstiprināts ✓' : 'Apstiprināt'}
                  </button>
                  <button
                    onClick={() => skip(c.id)}
                    className="bg-bg-subtle px-3 py-1 rounded text-sm"
                  >
                    Izņemt
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      {open && <PrepareTaskModal step="pick-stories" runId={run.id} onClose={() => setOpen(false)} />}
    </div>
  );
}

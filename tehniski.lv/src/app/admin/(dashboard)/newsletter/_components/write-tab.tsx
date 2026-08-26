'use client';
import { useState, useEffect } from 'react';
import { PrepareTaskModal } from './prepare-task-modal';

type Selection = {
  id: string;
  rank: number;
  approved: boolean;
  post_id: string | null;
  scraped_story: { id: string; title: string; url: string; source: { name: string } };
  post: { id: string; title: string; slug: string; status: string } | null;
};

type Post = { id: string; title: string; status: string; slug: string };

type Run = {
  id: string;
  status: string;
  selections: Selection[];
  posts: Post[];
};

export function WriteTab({ run, activeSelectionId }: { run: Run; activeSelectionId: string | null }) {
  const [open, setOpen] = useState<{ selectionId: string } | null>(null);
  const approved = run.selections.filter((s) => s.approved);

  // If the page was loaded with ?selection=<id>, open that selection's modal immediately
  useEffect(() => {
    if (activeSelectionId) {
      setOpen({ selectionId: activeSelectionId });
    }
  }, [activeSelectionId]);

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <div>
          <h2 className="text-lg font-bold">Rakstīšana</h2>
          <p className="text-xs text-text-secondary font-mono">
            {approved.length} apstiprināts stāsti; {approved.filter((s) => s.post_id).length} jau uzrakstīti
          </p>
        </div>
      </div>

      {approved.length === 0 ? (
        <p className="text-text-secondary text-sm">
          Nav apstiprinātu stāstu. Dodieties uz cilni "Redaktors" un apstipriniet vismaz vienu.
        </p>
      ) : (
        <div className="space-y-2">
          {approved.map((s) => (
            <div key={s.id} className="bg-bg-elevated border border-border rounded-md p-3">
              <div className="flex justify-between items-start gap-3">
                <div>
                  <div className="font-bold">
                    #{s.rank} {s.scraped_story.title}
                  </div>
                  <div className="text-xs text-text-secondary font-mono">
                    {s.scraped_story.source.name} · {s.scraped_story.url}
                  </div>
                  {s.post && (
                    <p className="text-xs text-text-secondary mt-1 font-mono">
                      Post: {s.post.title} · statuss: {s.post.status} · slug: {s.post.slug}
                    </p>
                  )}
                </div>
                <div className="shrink-0">
                  {s.post_id ? (
                    <span className="text-success text-sm font-mono">Uzrakstīts ✓</span>
                  ) : (
                    <button
                      onClick={() => setOpen({ selectionId: s.id })}
                      className="bg-accent-primary text-bg-base font-bold px-3 py-1 rounded text-sm"
                    >
                      Rakstīt
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {open && (
        <PrepareTaskModal
          step="write"
          runId={run.id}
          selectionId={open.selectionId}
          onClose={() => setOpen(null)}
        />
      )}
    </div>
  );
}

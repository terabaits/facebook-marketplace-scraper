'use client';
import { useState } from 'react';
import { PrepareTaskModal } from './prepare-task-modal';
import { useRouter } from 'next/navigation';

type Run = {
  id: string;
  status: string;
  subject_main: string | null;
  subject_alternatives: unknown;
  selected_subject: string | null;
  selections: Array<{ id: string; approved: boolean }>;
};

export function SubjectTab({ run }: { run: Run }) {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const alternatives: string[] = Array.isArray(run.subject_alternatives)
    ? (run.subject_alternatives as string[])
    : [];
  const candidates = [run.subject_main, ...alternatives].filter(Boolean) as string[];

  const approvedCount = run.selections.filter((s) => s.approved).length;

  async function pickSubject(subject: string) {
    await fetch(`/api/admin/newsletter/${run.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ selected_subject: subject })
    });
    router.refresh();
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <div>
          <h2 className="text-lg font-bold">Temata nosaukums</h2>
          <p className="text-xs text-text-secondary font-mono">
            {approvedCount} apstiprināts stāsti; izvēlies newsletter tematu
          </p>
        </div>
        <button
          onClick={() => setOpen(true)}
          className="bg-accent-primary text-bg-base font-bold px-4 py-2 rounded"
        >
          Sagatavot uzdevumu
        </button>
      </div>

      {candidates.length === 0 ? (
        <p className="text-text-secondary text-sm">
          Nav temata variantu. Palaid uzdevumu, lai Mavis piedāvātu temata nosaukumu.
        </p>
      ) : (
        <div className="space-y-2">
          {candidates.map((subject, i) => {
            const isSelected = run.selected_subject === subject;
            return (
              <div
                key={`${i}-${subject}`}
                className={`bg-bg-elevated border rounded-md p-3 flex justify-between items-center ${
                  isSelected ? 'border-success' : 'border-border'
                }`}
              >
                <div>
                  <div className="font-bold">
                    {i === 0 ? 'Galvenais: ' : `Alternatīva ${i}: `}
                    {subject}
                  </div>
                </div>
                <button
                  onClick={() => pickSubject(subject)}
                  className={
                    isSelected
                      ? 'bg-success text-bg-base px-3 py-1 rounded text-sm shrink-0'
                      : 'bg-bg-subtle px-3 py-1 rounded text-sm shrink-0'
                  }
                >
                  {isSelected ? 'Izvēlēts ✓' : 'Izvēlēties'}
                </button>
              </div>
            );
          })}
        </div>
      )}
      {open && <PrepareTaskModal step="pick-subject" runId={run.id} onClose={() => setOpen(false)} />}
    </div>
  );
}

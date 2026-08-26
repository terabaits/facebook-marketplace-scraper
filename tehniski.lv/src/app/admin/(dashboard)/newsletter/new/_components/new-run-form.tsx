'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

export function NewRunForm() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const fd = new FormData(e.currentTarget);
    const data = {
      target_date: fd.get('target_date'),
      previous_run_text: (fd.get('previous_run_text') as string) || undefined
    };
    const res = await fetch('/api/admin/newsletter', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (res.ok) {
      const run = await res.json();
      router.push(`/admin/newsletter/${run.id}`);
      router.refresh();
    } else {
      const e = await res.json().catch(() => ({}));
      setError(e.error ?? 'Kļūda');
      setBusy(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3 max-w-2xl mt-6">
      <label className="block text-sm">
        Mērķa datums
        <input
          name="target_date"
          type="date"
          required
          className="mt-1 w-full bg-bg-elevated border border-border rounded-md px-3 py-2 font-mono text-sm"
        />
      </label>
      <label className="block text-sm">
        Iepriekšējā izdevuma teksts (neobligāts; palīdz izvairīties no atkārtošanās)
        <textarea
          name="previous_run_text"
          rows={6}
          placeholder="Ielīmē iepriekšējā newsletter izdevuma tekstu, lai Mavis izvairītos no atkārtošanās."
          className="mt-1 w-full bg-bg-elevated border border-border rounded-md px-3 py-2 font-mono text-xs"
        />
      </label>
      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={busy}
          className="bg-accent-primary text-bg-base font-bold px-4 py-2 rounded disabled:opacity-50"
        >
          {busy ? 'Veido…' : 'Izveidot izdevumu'}
        </button>
        {error && <span className="text-sm text-danger">{error}</span>}
      </div>
    </form>
  );
}

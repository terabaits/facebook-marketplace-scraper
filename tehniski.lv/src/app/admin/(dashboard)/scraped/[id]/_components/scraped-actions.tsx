'use client';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

export function ScrapedActions({ id, status }: { id: string; status: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  async function patch(s: string) {
    setBusy(true);
    await fetch(`/api/admin/scraped/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status: s }) });
    router.refresh();
    setBusy(false);
  }
  return (
    <div className="flex gap-2">
      {status !== 'used' && <button onClick={() => patch('used')} disabled={busy} className="bg-success text-bg-base px-3 py-1 rounded text-sm">Izmantots</button>}
      {status !== 'ignored' && <button onClick={() => patch('ignored')} disabled={busy} className="bg-bg-subtle px-3 py-1 rounded text-sm">Ignorēt</button>}
      {status !== 'failed' && <button onClick={() => patch('failed')} disabled={busy} className="bg-warning text-bg-base px-3 py-1 rounded text-sm">Neizdevās</button>}
    </div>
  );
}

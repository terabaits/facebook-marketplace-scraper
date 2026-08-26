'use client';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

export function ModerationActions({ commentId }: { commentId: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  async function patch(status: string) {
    setBusy(true);
    await fetch(`/api/admin/comments/${commentId}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status }) });
    router.refresh();
    setBusy(false);
  }
  return (
    <div className="flex gap-2">
      <button onClick={() => patch('approved')} disabled={busy} className="bg-success text-bg-base px-2 py-1 rounded text-xs">Apstiprināt</button>
      <button onClick={() => patch('spam')} disabled={busy} className="bg-warning text-bg-base px-2 py-1 rounded text-xs">Spams</button>
      <button onClick={() => patch('deleted')} disabled={busy} className="bg-danger text-bg-base px-2 py-1 rounded text-xs">Dzēst</button>
    </div>
  );
}

'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

export function FetchNowButton({ sourceId }: { sourceId: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function handleClick() {
    setBusy(true);
    setMessage('Sūta pieprasījumu...');
    try {
      const res = await fetch(`/api/admin/sources/${sourceId}/fetch-now`, { method: 'POST' });
      const data = await res.json();
      setMessage(data.message ?? data.error ?? 'Nezināma atbilde');
      router.refresh();
    } catch (e: any) {
      setMessage(e.message);
    }
    setBusy(false);
  }

  return (
    <div className="flex items-center gap-3 mb-4">
      <button
        onClick={handleClick}
        disabled={busy}
        className="bg-warning text-bg-base font-bold px-3 py-1 rounded text-sm disabled:opacity-50"
      >
        {busy ? 'Sūta...' : 'Fetch now'}
      </button>
      {message && <span className="text-sm text-text-secondary">{message}</span>}
    </div>
  );
}

'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

export type StepName = 'pick-stories' | 'pick-subject' | 'write';

export function PrepareTaskModal({
  step,
  runId,
  selectionId,
  onClose
}: {
  step: StepName;
  runId: string;
  selectionId?: string;
  onClose: () => void;
}) {
  const router = useRouter();
  const [packet, setPacket] = useState<string | null>(null);
  const [response, setResponse] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function loadPacket() {
    setBusy(true);
    setError(null);
    const url = selectionId
      ? `/api/admin/newsletter/${runId}/packet/${step}?selection_id=${selectionId}`
      : `/api/admin/newsletter/${runId}/packet/${step}`;
    const res = await fetch(url);
    if (res.ok) {
      const md = await res.text();
      setPacket(md);
    } else {
      setError('Neizdevās ielādēt uzdevumu');
    }
    setBusy(false);
  }

  async function copyPacket() {
    if (!packet) return;
    await navigator.clipboard.writeText(packet);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  async function submit() {
    setBusy(true);
    setError(null);
    const res = await fetch(`/api/admin/newsletter/${runId}/submit/${step}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ response, selection_id: selectionId })
    });
    if (res.ok) {
      router.refresh();
      onClose();
    } else {
      const e = await res.json().catch(() => ({}));
      setError(e.error ?? 'Kļūda');
      setBusy(false);
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50"
      onClick={onClose}
    >
      <div
        className="bg-bg-base border border-border rounded-lg p-6 max-w-4xl w-full max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-xl font-bold mb-4">Uzdevums Mavis</h2>
        {!packet ? (
          <button
            onClick={loadPacket}
            disabled={busy}
            className="bg-accent-primary text-bg-base font-bold px-4 py-2 rounded"
          >
            {busy ? 'Ielādē…' : 'Sagatavot uzdevumu'}
          </button>
        ) : (
          <>
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm text-text-secondary">
                Nokopē šo uzdevumu un ielīmē to Mavis čatā:
              </span>
              <button onClick={copyPacket} className="bg-bg-subtle px-3 py-1 rounded text-sm">
                {copied ? 'Nokopēts ✓' : 'Kopēt uzdevumu'}
              </button>
            </div>
            <pre className="bg-bg-subtle border border-border rounded p-3 font-mono text-xs whitespace-pre-wrap overflow-auto flex-1 min-h-0 mb-4">
              {packet}
            </pre>
            <label className="block text-sm mb-1">Mavis atbilde (JSON):</label>
            <textarea
              value={response}
              onChange={(e) => setResponse(e.target.value)}
              rows={6}
              className="w-full bg-bg-elevated border border-border rounded-md px-3 py-2 font-mono text-xs"
            />
            {error && <p className="text-sm text-danger mt-2">{error}</p>}
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={onClose} className="px-3 py-1 rounded text-sm">
                Atcelt
              </button>
              <button
                onClick={submit}
                disabled={busy || !response.trim()}
                className="bg-accent-primary text-bg-base font-bold px-4 py-2 rounded disabled:opacity-50"
              >
                {busy ? 'Sūta…' : 'Iesniegt atbildi'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

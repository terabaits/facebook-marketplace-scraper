'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

export function PromptForm({ active }: { active: any }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function saveAsV2(form: HTMLFormElement, setActive: boolean) {
    setBusy(true); setMessage(null);
    const fd = new FormData(form);
    const data = {
      key: active.key,
      name: fd.get('name'),
      description: fd.get('description'),
      system_prompt: fd.get('system_prompt'),
      user_prompt: fd.get('user_prompt'),
      model: fd.get('model'),
      temperature: parseFloat(fd.get('temperature') as string),
      set_active: setActive
    };
    const res = await fetch('/api/admin/prompts', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data)
    });
    if (res.ok) {
      setMessage(setActive ? 'Jauna versija saglabāta un aktivizēta' : 'Jauna versija saglabāta (nav aktīva)');
      router.refresh();
    } else {
      const e = await res.json().catch(() => ({}));
      setMessage(e.error ?? 'Kļūda');
    }
    setBusy(false);
  }

  return (
    <form className="space-y-3 max-w-3xl" onSubmit={(e) => { e.preventDefault(); saveAsV2(e.currentTarget, false); }}>
      <input name="name" defaultValue={active.name} placeholder="Nosaukums" required className="w-full bg-bg-elevated border border-border rounded-md px-3 py-2" />
      <input name="description" defaultValue={active.description ?? ''} placeholder="Apraksts" className="w-full bg-bg-elevated border border-border rounded-md px-3 py-2" />
      <label className="block text-sm">System prompt
        <textarea name="system_prompt" defaultValue={active.system_prompt} required rows={8} className="w-full bg-bg-elevated border border-border rounded-md px-3 py-2 font-mono text-sm" />
      </label>
      <label className="block text-sm">User prompt
        <textarea name="user_prompt" defaultValue={active.user_prompt} required rows={3} className="w-full bg-bg-elevated border border-border rounded-md px-3 py-2 font-mono text-sm" />
      </label>
      <div className="flex gap-3">
        <label className="block text-sm flex-1">Modelis
          <input name="model" defaultValue={active.model} className="w-full bg-bg-elevated border border-border rounded-md px-3 py-2 font-mono text-sm" />
        </label>
        <label className="block text-sm flex-1">Temperature
          <input name="temperature" type="number" step="0.1" min="0" max="2" defaultValue={active.temperature} className="w-full bg-bg-elevated border border-border rounded-md px-3 py-2 font-mono text-sm" />
        </label>
      </div>
      <div className="flex items-center gap-3">
        <button type="submit" disabled={busy} className="bg-bg-subtle px-3 py-1 rounded text-sm">Saglabāt kā jaunu versiju</button>
        <button type="button" disabled={busy} onClick={(e) => saveAsV2(e.currentTarget.form!, true)} className="bg-accent-primary text-bg-base font-bold px-3 py-1 rounded text-sm">Saglabāt + aktivizēt</button>
        {message && <span className="text-sm text-text-secondary">{message}</span>}
      </div>
    </form>
  );
}

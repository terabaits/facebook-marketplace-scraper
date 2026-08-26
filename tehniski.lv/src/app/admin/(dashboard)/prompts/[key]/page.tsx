import { db } from '@/lib/db';
import { notFound } from 'next/navigation';
import { PromptForm } from '../_components/prompt-form';
import { formatDateLv } from '@/lib/format';

export default async function EditPromptPage({ params }: { params: Promise<{ key: string }> }) {
  const { key } = await params;
  const versions = await db.promptTemplate.findMany({
    where: { key },
    orderBy: { version: 'desc' }
  });
  if (versions.length === 0) notFound();
  const active = versions.find(v => v.active) ?? versions[0];
  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">{active.name}</h1>
      <p className="text-text-secondary text-sm mb-6 font-mono">key: {key} · aktīvā versija: v{active.version}</p>
      <PromptForm active={active} />
      <h2 className="text-lg font-bold mt-8 mb-2">Visas versijas</h2>
      <ul className="text-sm space-y-1">
        {versions.map(v => (
          <li key={v.id} className="font-mono">
            v{v.version} {v.active && <span className="text-success">• aktīvs</span>} · {formatDateLv(v.created_at)}
          </li>
        ))}
      </ul>
    </div>
  );
}

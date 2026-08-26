const labels: Record<string, string> = {
  draft: 'Melnraksts',
  scheduled: 'Plānots',
  published: 'Publicēts',
  archived: 'Arhivēts'
};

const colors: Record<string, string> = {
  draft: 'bg-text-secondary',
  scheduled: 'bg-warning',
  published: 'bg-success',
  archived: 'bg-bg-subtle'
};

export function PostStatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded text-xs font-mono text-bg-base ${colors[status] ?? 'bg-bg-subtle'}`}
    >
      {labels[status] ?? status}
    </span>
  );
}

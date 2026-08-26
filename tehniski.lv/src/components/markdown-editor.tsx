'use client';
import { useEffect, useState } from 'react';

export function MarkdownEditor({ name, defaultValue }: { name: string; defaultValue: string }) {
  const [value, setValue] = useState(defaultValue);
  const [preview, setPreview] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await fetch('/api/admin/preview-markdown', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ md: value })
        });
        if (res.ok) {
          const data = await res.json();
          setPreview(data.html);
        }
      } finally {
        setLoading(false);
      }
    }, 300); // debounce
    return () => clearTimeout(timer);
  }, [value]);

  return (
    <div className="grid grid-cols-2 gap-4">
      <textarea name={name} value={value} onChange={e => setValue(e.target.value)}
        className="font-mono text-sm bg-bg-elevated border border-border rounded-md p-3 h-96" />
      <div className="prose prose-invert bg-bg-elevated border border-border rounded-md p-3 h-96 overflow-auto"
        dangerouslySetInnerHTML={{ __html: preview || (loading ? '<p class="text-text-secondary">Ielādē...</p>' : '') }} />
    </div>
  );
}

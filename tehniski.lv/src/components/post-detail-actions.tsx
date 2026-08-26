'use client';
import { useState } from 'react';
import { Link as LinkIcon, Check, ExternalLink } from 'lucide-react';
import { lv } from '@/lib/lv';

type Props = {
  url: string;             // absolute post URL (used for share intents)
  title: string;           // post title (used for share text)
  sourceUrl?: string | null; // optional link back to the original article (newsletter posts)
};

export function PostDetailActions({ url, title, sourceUrl }: Props) {
  const [copied, setCopied] = useState(false);

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Older browsers / insecure context: best-effort fallback using a temp input.
      const el = document.createElement('input');
      el.value = url;
      document.body.appendChild(el);
      el.select();
      try { document.execCommand('copy'); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch { /* noop */ }
      document.body.removeChild(el);
    }
  }

  const enc = encodeURIComponent;
  const fbHref = `https://www.facebook.com/sharer/sharer.php?u=${enc(url)}`;
  const xHref  = `https://twitter.com/intent/tweet?url=${enc(url)}&text=${enc(title)}`;
  const waHref = `https://wa.me/?text=${enc(`${title} ${url}`)}`;

  // Reusable pill style — matches the "border / hover-bg-subtle" pattern used elsewhere.
  const pillBase = 'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-border text-sm hover:bg-bg-subtle transition-colors';

  return (
    <div className="mt-8 flex flex-wrap items-center gap-2 border-t border-border pt-6" role="group" aria-label={lv.post.share}>
      <span className="font-mono text-xs text-text-secondary uppercase mr-1">{lv.post.share}</span>

      <button
        type="button"
        onClick={copyLink}
        aria-label={lv.share.copyLink}
        aria-live="polite"
        className={pillBase}
      >
        {copied ? <Check size={14} /> : <LinkIcon size={14} />}
        {copied ? lv.share.copied : lv.share.copyLink}
      </button>

      <a href={fbHref} target="_blank" rel="noopener noreferrer" aria-label={`${lv.share.facebook} — ${title}`} className={pillBase}>
        {lv.share.facebook}
      </a>

      <a href={xHref} target="_blank" rel="noopener noreferrer" aria-label={`${lv.share.x} — ${title}`} className={pillBase}>
        {lv.share.x}
      </a>

      <a href={waHref} target="_blank" rel="noopener noreferrer" aria-label={`${lv.share.whatsapp} — ${title}`} className={pillBase}>
        {lv.share.whatsapp}
      </a>

      {sourceUrl && (
        <a href={sourceUrl} target="_blank" rel="noopener noreferrer" aria-label={lv.share.viewOriginal} className={pillBase}>
          <ExternalLink size={14} />
          {lv.share.viewOriginal}
        </a>
      )}
    </div>
  );
}

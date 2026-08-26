import { db } from '@/lib/db';
import { notFound } from 'next/navigation';
import { EditorTab } from '../_components/editor-tab';
import { SubjectTab } from '../_components/subject-tab';
import { WriteTab } from '../_components/write-tab';
import { PublishTab } from '../_components/publish-tab';
import Link from 'next/link';
import { formatDateLv } from '@/lib/format';

export default async function NewsletterDetailPage({
  params,
  searchParams
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ tab?: string; selection?: string }>;
}) {
  const { id } = await params;
  const { tab, selection } = await searchParams;
  const run = await db.newsletterRun.findUnique({
    where: { id },
    include: {
      selections: {
        orderBy: { rank: 'asc' },
        include: { scraped_story: { include: { source: { select: { name: true } } } }, post: true }
      },
      posts: true
    }
  });
  if (!run) notFound();

  const activeTab =
    tab ??
    (run.status === 'awaiting_editor'
      ? 'editor'
      : run.status === 'awaiting_subject'
        ? 'subject'
        : run.status === 'writing'
          ? 'write'
          : 'publish');

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">Newsletter · {formatDateLv(run.target_date)}</h1>
        <Link href="/admin/newsletter" className="text-sm text-text-secondary hover:text-accent-primary">
          ← Atpakaļ
        </Link>
      </div>
      <p className="text-text-secondary text-sm mb-4 font-mono">
        status: {run.status} · {run.selections.length} kandidāti · {run.posts.length} raksti
      </p>

      <nav className="flex gap-4 border-b border-border mb-6 text-sm">
        <Link
          href={`/admin/newsletter/${id}?tab=editor`}
          className={activeTab === 'editor' ? 'font-bold border-b-2 border-accent-primary py-2' : 'py-2'}
        >
          1. Redaktors
        </Link>
        <Link
          href={`/admin/newsletter/${id}?tab=subject`}
          className={activeTab === 'subject' ? 'font-bold border-b-2 border-accent-primary py-2' : 'py-2'}
        >
          2. Temats
        </Link>
        <Link
          href={`/admin/newsletter/${id}?tab=write`}
          className={activeTab === 'write' ? 'font-bold border-b-2 border-accent-primary py-2' : 'py-2'}
        >
          3. Rakstīšana
        </Link>
        <Link
          href={`/admin/newsletter/${id}?tab=publish`}
          className={activeTab === 'publish' ? 'font-bold border-b-2 border-accent-primary py-2' : 'py-2'}
        >
          4. Publicēšana
        </Link>
      </nav>

      {activeTab === 'editor' && <EditorTab run={run} />}
      {activeTab === 'subject' && <SubjectTab run={run} />}
      {activeTab === 'write' && <WriteTab run={run} activeSelectionId={selection ?? null} />}
      {activeTab === 'publish' && <PublishTab run={run} />}
    </div>
  );
}

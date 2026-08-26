import Link from 'next/link';
import { db } from '@/lib/db';
import { SignOutButton } from './sign-out-button';

export async function AdminNav({ userEmail }: { userEmail: string }) {
  const [pendingComments, scheduledPosts, totalPosts, totalScraped] = await Promise.all([
    db.comment.count({ where: { status: 'pending' } }),
    db.post.count({ where: { status: 'scheduled' } }),
    db.post.count({ where: { status: 'published' } }),
    db.scrapedStory.count()
  ]);
  return (
    <nav className="border-b border-border bg-bg-elevated">
      <div className="max-w-6xl mx-auto px-4 h-12 flex items-center justify-between text-sm">
        <div className="flex gap-6">
          <Link href="/admin">Panelis</Link>
          <Link href="/admin/posts">Raksti</Link>
          <Link href="/admin/sources">Avoti</Link>
          <Link href="/admin/scraped">Stāsti{totalScraped > 0 && <span className="ml-1 text-text-secondary font-mono text-xs">{totalScraped}</span>}</Link>
          <Link href="/admin/comments">Komentāri{pendingComments > 0 && <span className="ml-1 inline-block w-2 h-2 rounded-full bg-danger" />}</Link>
          <Link href="/admin/ads">Reklāmas</Link>
          <Link href="/admin/analytics">Analītika</Link>
          <Link href="/admin/settings">Iestatījumi</Link>
          <Link href="/admin/prompts">Prompti</Link>
          <Link href="/admin/newsletter">Newsletter</Link>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-text-secondary font-mono text-xs">{userEmail}</span>
          <SignOutButton />
        </div>
      </div>
    </nav>
  );
}

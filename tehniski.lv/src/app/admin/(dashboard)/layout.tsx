import { redirect } from 'next/navigation';
import { getSessionOrDevBypass, isDevBypassEnabled } from '@/lib/auth';
import { AdminNav } from '../_components/admin-nav';

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const session = await getSessionOrDevBypass();
  if (!session) redirect('/admin/login');
  return (
    <div className="min-h-screen flex flex-col">
      {isDevBypassEnabled() && (
        <div className="bg-warning text-bg-base text-xs font-bold text-center py-1">
          DEV AUTH BYPASS ACTIVE — set DEV_BYPASS_ADMIN_AUTH=0 (or remove the var) before production
        </div>
      )}
      <AdminNav userEmail={session.user?.email ?? ''} />
      <div className="flex-1 max-w-6xl mx-auto w-full px-4 py-8">{children}</div>
    </div>
  );
}

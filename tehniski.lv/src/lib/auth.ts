import NextAuth from 'next-auth';
import Resend from 'next-auth/providers/resend';
import { PrismaAdapter } from '@auth/prisma-adapter';
import { db } from '@/lib/db';
import { sendMagicLinkEmail } from '@/lib/email';

export const { handlers, auth, signIn, signOut } = NextAuth({
  adapter: PrismaAdapter(db),
  providers: [
    Resend({
      from: process.env.RESEND_FROM_EMAIL ?? 'noreply@tehniski.lv',
      apiKey: process.env.RESEND_API_KEY,
      async sendVerificationRequest({ identifier, url }) {
        await sendMagicLinkEmail(identifier, url);
      }
    })
  ],
  pages: { signIn: '/admin/login' },
  callbacks: {
    async signIn({ user }) {
      if (user.email) {
        await db.author.upsert({
          where: { email: user.email },
          update: { is_admin: true },
          create: { email: user.email, name: user.name ?? user.email, is_admin: true }
        });
      }
      return true;
    },
    async session({ session }) {
      if (session.user?.email) {
        const author = await db.author.findUnique({ where: { email: session.user.email } });
        if (author) (session.user as any).is_admin = author.is_admin;
      }
      return session;
    }
  }
});

/**
 * DEV-ONLY: Returns true when the developer has explicitly opted in to bypass
 * admin authentication. Used by `requireSession` in the admin layout and admin
 * API routes so the protected screens can be exercised end-to-end before the
 * Auth.js User/Account/Session/VerificationToken tables are added in a later
 * task. Remove this flag (and the env var) before deploying to production.
 */
export function isDevBypassEnabled(): boolean {
  return process.env.DEV_BYPASS_ADMIN_AUTH === '1';
}

/**
 * Returns the current session, or `null` when the visitor is not authenticated
 * AND the dev bypass is not active. Layouts and API routes should call this
 * instead of `auth()` directly so the bypass applies uniformly.
 */
export async function getSessionOrDevBypass() {
  const session = await auth();
  if (session) return session;
  if (isDevBypassEnabled()) {
    return { user: { email: 'dev@local', name: 'Dev Bypass', is_admin: true } } as any;
  }
  return null;
}

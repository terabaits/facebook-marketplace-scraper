'use client';
import { signIn } from 'next-auth/react';
import { useState } from 'react';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  return (
    <div className="max-w-md mx-auto py-16 px-4">
      <h1 className="text-2xl font-bold mb-4">Pieteikšanās</h1>
      {sent ? (
        <p className="text-text-secondary">Mēs nosūtījām saiti uz {email}. Pārbaudiet savu e-pastu.</p>
      ) : (
        <form onSubmit={async (e) => {
          e.preventDefault();
          setError(null);
          try {
            await signIn('resend', { email, redirect: false });
            setSent(true);
          } catch (err: any) {
            setError(err?.message ?? 'Kļūda');
          }
        }}>
          <input type="email" required value={email} onChange={e => setEmail(e.target.value)} placeholder="E-pasts"
            className="w-full bg-bg-elevated border border-border rounded-md px-4 py-2 mb-3" />
          <button type="submit" className="w-full bg-accent-primary text-bg-base font-bold py-2 rounded-md">Nosūtīt saiti</button>
          {error && <p className="mt-3 text-sm text-danger">{error}</p>}
        </form>
      )}
    </div>
  );
}

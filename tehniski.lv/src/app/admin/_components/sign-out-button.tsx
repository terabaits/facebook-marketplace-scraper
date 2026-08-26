'use client';
import { signOut } from 'next-auth/react';

export function SignOutButton() {
  return <button onClick={() => signOut()} className="text-text-secondary hover:text-danger">Iziet</button>;
}

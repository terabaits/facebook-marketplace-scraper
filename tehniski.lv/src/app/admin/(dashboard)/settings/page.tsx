import { db } from '@/lib/db';
import { SettingsForm } from './_components/settings-form';

export default async function SettingsPage() {
  const settings = await db.setting.findMany();
  const map = Object.fromEntries(settings.map(s => [s.key, s.value]));
  return <div><h1 className="text-2xl font-bold mb-6">Iestatījumi</h1><SettingsForm initial={map} /></div>;
}

import { db } from '../src/lib/db';

async function main() {
  const rows = await db.$queryRaw<{ ok: number }[]>`SELECT 1 as ok`;
  console.log('Query result:', rows);
  const tableCount = await db.$queryRaw<{ count: bigint }[]>`
    SELECT count(*)::bigint as count FROM information_schema.tables WHERE table_schema = 'public'
  `;
  console.log('Table count:', tableCount);
  await db.$disconnect();
}

main().catch((e) => {
  console.error('Error:', e);
  process.exit(1);
});

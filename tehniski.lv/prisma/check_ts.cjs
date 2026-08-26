const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();
(async () => {
  console.log('--- Verification 1: search vector query ---');
  try {
    const rows = await prisma.$queryRawUnsafe(
      "SELECT title FROM \"Post\" WHERE search_vector @@ to_tsquery('latvian', 'test');"
    );
    console.log('Query succeeded. Rows:', rows.length, JSON.stringify(rows));
  } catch (e) {
    console.error('Query error:', e.message);
  }

  console.log('--- Verification 2: latvian collation exists ---');
  try {
    const rows = await prisma.$queryRawUnsafe(
      "SELECT collname, collprovider FROM pg_collation WHERE collname = 'latvian';"
    );
    console.log('Collation:', rows);
  } catch (e) {
    console.error('Error:', e.message);
  }

  console.log('--- Verification 3: search_vector column + GIN index ---');
  try {
    const cols = await prisma.$queryRawUnsafe(
      "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'Post' AND column_name = 'search_vector';"
    );
    console.log('Column:', cols);
    const idx = await prisma.$queryRawUnsafe(
      "SELECT indexname, indexdef FROM pg_indexes WHERE indexname IN ('post_search_vector_idx', 'post_scheduled_publish_idx', 'prompt_active_unique');"
    );
    console.log('Indexes:', idx);
  } catch (e) {
    console.error('Error:', e.message);
  }

  await prisma.$disconnect();
})();

const { PrismaClient } = require('@prisma/client');
const db = new PrismaClient();
db.post.findMany({ select: { slug: true, title: true }, orderBy: { published_at: 'desc' } })
  .then(r => { console.log(JSON.stringify(r, null, 2)); return db.$disconnect(); })
  .catch(e => { console.error(e); process.exit(1); });

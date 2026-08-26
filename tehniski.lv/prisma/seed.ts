import { PrismaClient, PostStatus, FeaturedTier, SourceType } from '@prisma/client';
import { slugify } from '../src/lib/slug';
import { renderMarkdown } from '../src/lib/markdown';

const db = new PrismaClient();

const SAMPLE_BODY = (topic: string) => `# ${topic}

Šis ir izglītojošs raksts par ${topic}. Tehnoloģijas attīstās strauji, un mēs sekojam līdzi jaunākajām tendencēm.

## Galvenie punkti

- Pirmais punkts par ${topic}
- Otrais punkts ar piemēru
- Trešais punkts ar secinājumu

## Secinājums

Šī tēma ir svarīga, jo tā ietekmē ikvienu tehnoloģiju lietotāju.`;

async function main() {
  const author = await db.author.upsert({
    where: { email: 'admin@tehniski.lv' },
    update: {},
    create: { name: 'Redaktors', email: 'admin@tehniski.lv', is_admin: true, bio: 'tehniski.lv galvenais redaktors.' }
  });

  const categories = await Promise.all([
    db.category.upsert({ where: { slug: 'ai' }, update: {}, create: { slug: 'ai', name: 'AI' } }),
    db.category.upsert({ where: { slug: 'hardware' }, update: {}, create: { slug: 'hardware', name: 'Aparatūra' } }),
    db.category.upsert({ where: { slug: 'software' }, update: {}, create: { slug: 'software', name: 'Programmatūra' } }),
    db.category.upsert({ where: { slug: 'security' }, update: {}, create: { slug: 'security', name: 'Drošība' } })
  ]);

  const posts: Array<{ title: string; category: string; featured_tier: 'big' | 'medium' | null; days_ago: number }> = [
    { title: 'OpenAI laiž klajā jaunu GPT modeli', category: 'ai', featured_tier: 'big', days_ago: 0 },
    { title: 'Apple M4 Ultra oficiāli iznāk', category: 'hardware', featured_tier: 'big', days_ago: 0 },
    { title: 'Windows 12 pirmie soļi', category: 'software', featured_tier: 'medium', days_ago: 1 },
    { title: 'Linux 6.10 jaunumi', category: 'software', featured_tier: 'medium', days_ago: 1 },
    { title: 'Kiberdrošības pārskats 2026', category: 'security', featured_tier: 'medium', days_ago: 2 },
    { title: 'NVIDIA nākamais GPU', category: 'hardware', featured_tier: 'medium', days_ago: 2 },
    { title: 'Kā darbojas LLM', category: 'ai', featured_tier: null, days_ago: 3 },
    { title: 'Raspberry Pi 6 atjauninājums', category: 'hardware', featured_tier: null, days_ago: 4 },
    { title: 'GitHub Copilot jaunais plāns', category: 'software', featured_tier: null, days_ago: 5 },
    { title: '0-day ievainojamība Chrome', category: 'security', featured_tier: null, days_ago: 6 }
  ];

  for (let i = 0; i < posts.length; i++) {
    const p = posts[i];
    const cat = categories.find(c => c.slug === p.category)!;
    const baseSlug = slugify(p.title);
    const slug = `${baseSlug}-${i}`;
    const publishedAt = new Date(Date.now() - p.days_ago * 86_400_000);
    const body = SAMPLE_BODY(p.title);
    const html = renderMarkdown(body);
    await db.post.upsert({
      where: { slug },
      update: { content_md: body, content_html: html },
      create: {
        slug,
        title: p.title,
        excerpt: `Īss apraksts par ${p.title.toLowerCase()}.`,
        content_md: body,
        content_html: html,
        status: PostStatus.published,
        published_at: publishedAt,
        language: 'lv',
        source: SourceType.manual,
        author_id: author.id,
        category_id: cat.id,
        featured_tier: p.featured_tier as FeaturedTier | null,
        featured_at: p.featured_tier ? new Date() : null,
        featured_order: p.featured_tier === 'big' ? i : p.featured_tier === 'medium' ? i - 2 : null
      }
    });
  }

  // Also seed ad slots
  await db.adSlot.upsert({ where: { key: 'homepage_right_rail' }, update: {}, create: { key: 'homepage_right_rail', name: 'Sākumlapa — labais panelis', width: 300, height: 600 } });
  await db.adSlot.upsert({ where: { key: 'post_top' }, update: {}, create: { key: 'post_top', name: 'Raksts — augša', width: 970, height: 90 } });
  await db.adSlot.upsert({ where: { key: 'post_right_rail' }, update: {}, create: { key: 'post_right_rail', name: 'Raksts — labais panelis', width: 300, height: 600 } });

  // Seed default RSS sources (6 sources — all use cheerio/readability for v1)
  const sources = [
    { name: 'Digital Trends', feed_url: 'https://www.digitaltrends.com/feed/?key=f00edf6a58d2a8740e624dda919cab37', site_url: 'https://www.digitaltrends.com', parser_config: { kind: 'readability' } },
    { name: "Tom's Hardware", feed_url: 'https://www.tomshardware.com/feeds/all', site_url: 'https://www.tomshardware.com', parser_config: { kind: 'readability' } },
    { name: 'Windows Central', feed_url: 'https://www.windowscentral.com/rss', site_url: 'https://www.windowscentral.com', parser_config: { kind: 'readability' } },
    { name: 'Ars Technica', feed_url: 'https://feeds.arstechnica.com/arstechnica/features', site_url: 'https://arstechnica.com', parser_config: { kind: 'readability' } },
    { name: 'CBS News SciTech', feed_url: 'http://feeds.cbsnews.com/CBSNewsSciTech', site_url: 'https://www.cbsnews.com', parser_config: { kind: 'readability' } },
    { name: 'TechnoBuffalo', feed_url: 'https://www.technobuffalo.com/feed', site_url: 'https://www.technobuffalo.com', parser_config: { kind: 'readability' } }
  ];
  for (const s of sources) {
    await db.rssSource.upsert({ where: { feed_url: s.feed_url }, update: {}, create: s });
  }

  // Prompt templates (M3 editorial workflow)
  const prompts = [
    {
      key: 'pick-stories',
      name: 'Stāstu izvēle',
      description: 'Mavis izvēlas labākos stāstus no scraped pool un ģenerē intro + shortlist',
      system_prompt: `Tu esi pieredzējis tehnoloģiju ziņu redaktors latviešu valodā. Tava loma: izvēlēties 3-7 stāstus no kandidātu saraksta, kas būtu saistoši un svarīgi Latvijas tech auditorijai. Ņem vērā: 1) vai stāsts ir aktuāls; 2) vai tas ir interesants ne-tehniskai auditorijai; 3) vai tam ir pietiekami daudz satura dziļuma. Izvairies no Clickbait un no pārāk šaurām tehniskām nišām.`,
      user_prompt: 'Atgriez TIKAI JSON objektu ar laukiem: candidates[], intro, shortlist, iteration_notes',
      temperature: 0.7
    },
    {
      key: 'pick-subject',
      name: 'Temata nosaukums',
      description: 'Mavis izveido dienasnewsletter temata nosaukumu un 3-5 alternatīvas',
      system_prompt: `Tu esi redaktors, kas raksta saistošus temata nosaukumus (subject line) latviešu valodā tech-ziņu newsletter. Tavam subject jābūt: 1) īsam (līdz 80 rakstzīmēm); 2) informatīvam, nevis clickbait; 3) atspoguļo dienas galveno tēmu. Alternatīvas variē pēc stila (formāls, jautrs, provokatīvs).`,
      user_prompt: 'Atgriez TIKAI JSON objektu ar laukiem: main, alternatives[] (3-5)',
      temperature: 0.8
    },
    {
      key: 'write',
      name: 'Raksta pārstāsts',
      description: 'Mavis pārtulko un pārstrādā scraped rakstu latviski kā Post',
      system_prompt: `Tu esi tech-ziņu rakstnieks latviešu valodā. Tava loma: pārtulkot un adaptēt svešvalodas rakstu latviski, saglabājot faktus un idejas, bet pielāgojot stilu vietējai auditorijai. Raksti: 1) skaidrā, dabiskā latviešu valodā; 2) ar virsrakstiem (H2/H3); 3) ar konkrētiem piemēriem un skaitļiem; 4) bez clickbait un bez tulkojuma "smaržas". Markdown formātā.`,
      user_prompt: 'Atgriez TIKAI JSON objektu ar laukiem: title_lv, excerpt_lv, body_md',
      temperature: 0.6
    },
    {
      key: 'editorial-feedback',
      name: 'Redaktora atsauksmes',
      description: 'Sistēmas paziņojums, ko Mavis saņem, kad redaktors atkārtoti izvēlas stāstus ar atsauksmēm',
      system_prompt: 'Tu saņēmi iepriekšējo izvēli un redaktora atsauksmes. Ņem vērā atsauksmes un ģenerē jaunu, uzlabotu izvēli. Paskaidro, ko mainīji (iteration_notes laukā).',
      user_prompt: 'Atgriez TIKAI JSON objektu tāpat kā iepriekš, bet ar uzlabojumiem un iteration_notes lauku',
      temperature: 0.7
    }
  ];
  for (const p of prompts) {
    await db.promptTemplate.upsert({
      where: { key_version: { key: p.key, version: 1 } },
      update: { active: true },  // ensure seeded prompts are active
      create: { ...p, version: 1, model: 'unset', active: true }
    });
  }

  console.log('Seed complete');
}

main().then(() => db.$disconnect()).catch(e => { console.error(e); db.$disconnect(); process.exit(1); });

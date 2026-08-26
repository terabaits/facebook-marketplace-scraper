// Deep-verify the post page content
const url = 'http://localhost:5002/post/openai-lai%C5%BE-klaj%C4%81-jaunu-gpt-modeli-0';
(async () => {
  const r = await fetch(url);
  const html = await r.text();
  console.log('Status:', r.status, 'Length:', html.length);

  const checks = {
    'H1 contains OpenAI': /<h1[^>]*>[^<]*OpenAI/i.test(html),
    'H1 contains laiž': /<h1[^>]*>[^<]*laiž/i.test(html),
    'JSON-LD script tag': /<script[^>]*type="application\/ld\+json"/.test(html),
    'JSON-LD @type Article': /"@type":"Article"/.test(html),
    'JSON-LD headline OpenAI': /"headline":"OpenAI[^"]*"/.test(html),
    'JSON-LD publisher tehniski.lv': /"publisher":\s*{[^}]*"name":"tehniski\.lv"/.test(html),
    'JSON-LD author Redaktors': /"author":\s*\[[^\]]*"name":"Redaktors"/.test(html),
    'More-from section heading': /Vairāk no tehniski\.lv/.test(html),
    'Comments section heading': /Komentāri/.test(html),
    'Comments stub text': /Komentāru sistēma tiks pievienota drīzumā/.test(html),
    'Comments data-post-id': /data-post-id="[^"]+"/.test(html),
    'post_top ad slot': /Ad slot: post_top/.test(html),
    'post_right_rail ad slot': /Ad slot: post_right_rail/.test(html),
    'Category breadcrumb "AI"': /AI\s*·/.test(html),
    'Source_url footer (NOT seeded)': /Avots:/.test(html),
    'Post body (H1 OpenAI laiž klajā jaunu GPT modeli)': /OpenAI laiž klajā jaunu GPT modeli/.test(html),
    'Multiple /post/ links (self + 4 more-from)': (html.match(/href="\/post\//g) || []).length >= 5,
    'Has meta title with tehniski.lv': /<title>[^<]*tehniski\.lv/.test(html),
    'More-from PostCard count = 4': ((html.match(/Vairāk no tehniski\.lv[\s\S]{0,4000}?<\/section>/) || [''])[0].match(/href="\/post\//g) || []).length === 4
  };
  for (const [k, v] of Object.entries(checks)) {
    console.log(`${v ? '✓' : '✗'}  ${k}`);
  }
})();

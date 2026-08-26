function lvPlural(n: number, singular: string, plural: string): string {
  if (n === 1) return `${n} ${singular}`;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 19) return `${n} ${plural}`;
  const mod10 = n % 10;
  if (mod10 === 1) return `${n} ${singular}`;
  return `${n} ${plural}`;
}

export const lv = {
  common: { save: 'Saglabāt', cancel: 'Atcelt', delete: 'Dzēst', edit: 'Rediģēt', publish: 'Publicēt', draft: 'Melnraksts' },
  nav: { home: 'Sākums', categories: 'Kategorijas', search: 'Meklēt' },
  post: { comments: 'Komentāri', reply: 'Atbildēt', author: 'Autors', moreFrom: 'Vairāk no tehniski.lv', source: 'Avots', share: 'Dalīties', loadMore: 'Ielādēt vēl' },
  share: { copyLink: 'Kopēt saiti', copied: 'Nokopēts ✓', facebook: 'Facebook', x: 'X', whatsapp: 'WhatsApp', viewOriginal: 'Skatīt oriģinālu' },
  search: { title: 'Meklēšana', placeholder: 'Meklēt rakstus...', resultsFor: (q: string, n: number) => `${n} rezultāti vaicājumam "${q}"`, suggestionsHint: 'Ieteikumi', searchOnSite: 'Meklēt lapā' },
  notFound: { title: 'Lapa nav atrasta', lead: 'Meklētā lapa nepastāv vai ir pārvietota.', cta: 'Doties atpakaļ uz sākumlapu' },
  errorPage: { title: 'Kaut kas nogāja greizi', lead: 'Mēģiniet atsvaidzināt lapu vai meklēt kaut ko citu.', retry: 'Mēģināt vēlreiz' },
  comment: { placeholder: 'Ierakstiet komentāru...', submit: 'Iesniegt', pending: 'Gaida apstiprinājumu', author: 'Autors' },
  plural: { comments: (n: number) => lvPlural(n, 'komentārs', 'komentāri') },
  error: { notFound: 'Lapa nav atrasta', serverError: 'Kaut kas nogāja greizi' }
} as const;

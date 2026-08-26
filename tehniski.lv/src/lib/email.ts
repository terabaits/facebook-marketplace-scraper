import { Resend } from 'resend';

const apiKey = process.env.RESEND_API_KEY;
const from = process.env.RESEND_FROM_EMAIL ?? 'noreply@tehniski.lv';

export async function sendMagicLinkEmail(to: string, url: string) {
  if (!apiKey) {
    console.warn('RESEND_API_KEY not set — magic link:', url);
    return;
  }
  const resend = new Resend(apiKey);
  await resend.emails.send({
    from,
    to,
    subject: 'Piekļuve tehniski.lv administrācijai',
    html: `<p>Sveiki!</p><p>Noklikšķiniet uz saites, lai pieteiktos tehniski.lv administrācijā:</p><p><a href="${url}">${url}</a></p><p>Ja jūs to nepieprasījāt, ignorējiet šo e-pastu.</p>`
  });
}

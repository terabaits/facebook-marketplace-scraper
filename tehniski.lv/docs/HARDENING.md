# tehniski.lv — Operator Runbook

## Production deployment (Windows self-hosted)

This project is designed to run on the same Windows machine as the rest of your portfolio (alongside SS-WEBSITE on :5000 and idejuskapis on :5001). tehniski.lv uses port 5002.

### Prerequisites
- Node.js 20 LTS (via nvm or direct install)
- PostgreSQL 15+ on `localhost:5433` (shared with other projects)
- `nssm` on PATH (https://nssm.cc) for Windows Service installation
- `cloudflared` on PATH (https://github.com/cloudflare/cloudflared) for HTTPS via Cloudflare Tunnel
- `pg_dump` and `gzip` on PATH (for backups)
- `.env` filled in with real values (see `.env.example`)

### Initial setup

1. **Install dependencies**: `npm ci`
2. **Apply migrations**: `npx prisma migrate deploy`
3. **Seed the DB**: `npm run db:seed`
4. **Build for production**: `npm run build`
5. **Install the web service** (as Administrator):
   ```powershell
   .\scripts\install-services.ps1
   ```
6. **Verify the service**:
   - Open `http://localhost:5002/api/health` → should return `{"ok":true,"db":"up",...}`
   - `services.msc` → confirm `tehniski-lv-web` is running

### HTTPS via Cloudflare Tunnel

For a free HTTPS setup without opening inbound ports on your machine:

1. **Install `cloudflared`**: download from https://github.com/cloudflare/cloudflared/releases
2. **Login**: `cloudflared tunnel login`
3. **Create the tunnel**: `cloudflared tunnel create tehniski-lv`
4. **Route DNS**: `cloudflared tunnel route dns tehniski-lv tehniski.lv`
5. **Configure** by creating `%USERPROFILE%\.cloudflared\config.yml`:
   ```yaml
   tunnel: <TUNNEL_ID>
   credentials-file: C:\Users\<YOU>\.cloudflared\<TUNNEL_ID>.json
   ingress:
     - hostname: tehniski.lv
       service: http://localhost:5002
     - hostname: '*.tehniski.lv'
       service: http://localhost:5002
     - service: http_status:404
   ```
6. **Run as Windows Service** (recommended):
   ```powershell
   cloudflared service install
   ```

### Database backups

`scripts\pg-backup.ps1` dumps the `tehniski_lv` database to `backups\` with 7-day local retention. Schedule it via Windows Task Scheduler:

- **Trigger**: Daily at 03:00
- **Action**: Start a program
  - Program: `powershell.exe`
  - Arguments: `-ExecutionPolicy Bypass -File "G:\Github\tehniski.lv\scripts\pg-backup.ps1"`

For offsite backup, install `rclone` and add an extra step that copies `backups\` to Backblaze B2 (or any S3-compatible target). Document the bucket name and credential path in a follow-up.

### Uptime monitoring

1. Sign up at https://uptimerobot.com (free tier is fine)
2. Add a new monitor:
   - Type: HTTPS
   - URL: `https://tehniski.lv/api/health`
   - Interval: 5 minutes
   - Alert contacts: your email

### Service supervision

Both `next start` (web) and the future `next-worker` (RSS scraper, M2) are supervised by `nssm` with `AppExit Default Restart` and a 5-second restart delay. If a process crashes, it restarts automatically within seconds.

Check the running services:
```powershell
Get-Service tehniski-lv-web
```

View recent logs:
```powershell
Get-Content .\logs\web.err.log -Tail 50
```

### Recovery procedure

**Restore from backup** (if you have a `tehniski_lv-YYYY-MM-DD-HHMM.sql.gz` file):

```powershell
$env:PGPASSWORD = '...'
gunzip -c backups\tehniski_lv-YYYY-MM-DD-HHMM.sql.gz | psql -h localhost -p 5433 -U tehniski_lv -d tehniski_lv
```

This overwrites the current database. Be careful.

### Known issues / TODO

- **Real Auth.js flow**: Tasks 13-14 noted that magic-link sign-in requires the standard `User/Account/Session/VerificationToken` tables (PrismaAdapter doesn't have them yet). The dev-bypass via `DEV_BYPASS_ADMIN_AUTH=1` is currently active. To enable real sign-in: add the standard Auth.js Prisma tables to `prisma/schema.prisma` and run a migration.
- **Local image storage**: cover images and ad creatives go to `public/uploads/`. For production, switch to S3-compatible storage (Backblaze B2 recommended) by updating `src/app/api/admin/uploads/cover/route.ts`.
- **Resend domain verification**: `noreply@tehniski.lv` won't send until you verify the `tehniski.lv` domain in your Resend dashboard.
- **n8n-style newsletter pipeline** (M3) not yet built. The current admin panel only supports manual post creation.

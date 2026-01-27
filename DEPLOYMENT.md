# Deployment Guide for Project Civitas

## Cloudflare Pages Deployment

The site deploys to Cloudflare Pages via GitHub Actions.

### Setup (One-Time)

1. **Create Cloudflare Pages Project:**
   - Go to Cloudflare Dashboard > Pages
   - Create a new project named `civitas`
   - Or use Wrangler CLI:
     ```bash
     npx wrangler pages project create civitas
     ```

2. **Add GitHub Secrets:**
   Go to `github.com/baytides/civitas/settings/secrets/actions` and add:
   - `CLOUDFLARE_API_TOKEN` - Create at Cloudflare Dashboard > API Tokens (use "Edit Cloudflare Workers" template)
   - `CLOUDFLARE_ACCOUNT_ID` - Found in Cloudflare Dashboard URL or Overview page

3. **Configure Custom Domain:**
   - Go to Cloudflare Pages > civitas > Custom domains
   - Add `projectcivitas.com`
   - DNS will auto-configure since domain is on Cloudflare

### Deployment

Deployments happen automatically:
- **Push to `main`** → Production deploy to projectcivitas.com
- **Pull requests** → Preview deploy with unique URL

### Environment Variables

Set these in Cloudflare Pages > civitas > Settings > Environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URI` | PostgreSQL connection string | Yes |
| `PAYLOAD_SECRET` | Random secret for Payload CMS | Yes |
| `NEXT_PUBLIC_API_URL` | Backend API URL | Optional |
| `OLLAMA_HOST` | Ollama API endpoint | Optional |

### Manual Deploy

```bash
cd web
npm run build
npx wrangler pages deploy .next --project-name=civitas
```

---

## Current Status

- ✅ Code is on GitHub at `baytides/civitas`
- ✅ Next.js app builds successfully
- ✅ GitHub Actions workflow configured for Cloudflare Pages
- ⏳ Add `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` to GitHub Secrets
- ⏳ Create Cloudflare Pages project
- ⏳ Configure custom domain

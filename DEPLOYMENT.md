# Deployment Guide for Project Civitas

## Cloudflare Workers Deployment (OpenNext)

The site deploys to Cloudflare Workers using the OpenNext adapter via GitHub Actions.

### Setup (One-Time)

1. **Create Cloudflare Worker:**
   - Go to Cloudflare Dashboard > Workers & Pages
   - Create a new Worker named `civitas`

2. **Add GitHub Secrets:**
   Go to `github.com/baytides/civitas/settings/secrets/actions` and add:
   - `CLOUDFLARE_API_TOKEN` - Create at Cloudflare Dashboard > API Tokens (use "Edit Cloudflare Workers" template)
   - `CLOUDFLARE_ACCOUNT_ID` - Found in Cloudflare Dashboard URL or Overview page

3. **Configure Custom Domain:**
   - Go to Cloudflare Workers & Pages > civitas > Custom domains
   - Add `projectcivitas.com`
   - DNS will auto-configure since domain is on Cloudflare

### Deployment

Deployments happen automatically:
- **Push to `main`** → Production deploy to projectcivitas.com
- **Pull requests** → Preview deploy with unique URL

### Environment Variables

Set these in Cloudflare Workers > civitas > Settings > Variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URI` | PostgreSQL connection string | Yes |
| `PAYLOAD_SECRET` | Random secret for Payload CMS | Yes |
| `NEXT_PUBLIC_API_URL` | Backend API URL (browser) | Optional (defaults to `https://api.projectcivitas.com/api/v1`) |
| `FASTAPI_URL` | Backend API URL (build-time rewrites) | Optional (defaults to `https://api.projectcivitas.com`) |
| `OLLAMA_HOST` | Ollama API endpoint | Optional |

### KV Cache (Recommended)

OpenNext uses KV for incremental cache. Create a KV namespace and set the ID in
`web/wrangler.jsonc` under `NEXT_CACHE_KV`.

### Manual Deploy

```bash
cd web
npm run build:cloudflare
npx wrangler deploy --config wrangler.jsonc
```

---

## Current Status

- ✅ Code is on GitHub at `baytides/civitas`
- ✅ Next.js app builds successfully
- ✅ GitHub Actions workflow configured for Cloudflare Workers
- ⏳ Add `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` to GitHub Secrets
- ⏳ Create Cloudflare Worker
- ⏳ Configure custom domain

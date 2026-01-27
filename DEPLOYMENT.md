# Deployment Guide for Project Civitas

## Quick Summary

The site is not deployed yet. Here are your deployment options:

---

## Option 1: Vercel (Recommended - Easiest)

Vercel is the company behind Next.js and offers the simplest deployment.

### Steps:

1. Go to [vercel.com](https://vercel.com) and sign in with GitHub
2. Click "Import Project"
3. Select the `baytides/civitas` repository
4. Configure the project:
   - **Root Directory**: `web`
   - **Framework Preset**: Next.js (auto-detected)
5. Add Environment Variables:
   - `DATABASE_URI` - Your PostgreSQL connection string
   - `PAYLOAD_SECRET` - A random secret for Payload CMS
6. Click "Deploy"

### Custom Domain:
After deployment, go to Settings > Domains and add `projectcivitas.com`:
- Add both `projectcivitas.com` and `www.projectcivitas.com`
- Update your DNS with the provided records

---

## Option 2: Azure Static Web Apps

A GitHub Actions workflow has been created at `.github/workflows/deploy.yml`.

### Steps:

1. Create an Azure Static Web App in the Azure Portal:
   ```bash
   az staticwebapp create \
     --name civitas-web \
     --resource-group baytides-rg \
     --source https://github.com/baytides/civitas \
     --location westus2 \
     --branch main \
     --app-location "web" \
     --output-location ".next"
   ```

2. Get the deployment token:
   ```bash
   az staticwebapp secrets list --name civitas-web --query "properties.apiKey" -o tsv
   ```

3. Add the token to GitHub Secrets:
   - Go to `github.com/baytides/civitas/settings/secrets/actions`
   - Add secret: `AZURE_STATIC_WEB_APPS_API_TOKEN`

4. Push to main branch to trigger deployment

### Custom Domain:
```bash
az staticwebapp hostname set \
  --name civitas-web \
  --hostname projectcivitas.com
```

---

## Option 3: Self-Hosted (Docker)

For full control, you can deploy to any server with Docker.

### Dockerfile (create at `web/Dockerfile`):

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV production

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
ENV PORT 3000
CMD ["node", "server.js"]
```

### Deploy to your Azure VM:

```bash
# Build and push to Azure Container Registry
docker build -t civitas-web ./web
docker tag civitas-web baytidesstorage.azurecr.io/civitas-web:latest
docker push baytidesstorage.azurecr.io/civitas-web:latest

# Run on Azure VM
docker run -d -p 3000:3000 \
  -e DATABASE_URI=your_db_uri \
  -e PAYLOAD_SECRET=your_secret \
  baytidesstorage.azurecr.io/civitas-web:latest
```

---

## DNS Configuration

To point `projectcivitas.com` to your deployment:

### For Vercel:
```
Type    Name    Value
A       @       76.76.21.21
CNAME   www     cname.vercel-dns.com
```

### For Azure Static Web Apps:
Get the default hostname from Azure and create:
```
Type    Name    Value
CNAME   @       <your-app>.azurestaticapps.net
CNAME   www     <your-app>.azurestaticapps.net
```

---

## Environment Variables Required

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URI` | PostgreSQL connection string | Yes |
| `PAYLOAD_SECRET` | Random secret for Payload CMS | Yes |
| `NEXT_PUBLIC_API_URL` | Backend API URL | Optional |
| `OLLAMA_HOST` | Ollama API endpoint | Optional |

---

## Current Status

- ✅ Code is on GitHub at `baytides/civitas`
- ✅ Next.js app builds successfully
- ❌ No deployment configured yet
- ❌ Domain `projectcivitas.com` needs DNS configuration

## Next Steps

1. Choose a deployment option above
2. Configure environment variables
3. Deploy
4. Update DNS to point domain to deployment
5. Verify site is live at projectcivitas.com

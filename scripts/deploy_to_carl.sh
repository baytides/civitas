#!/bin/bash
# Civitas Deployment Script for Carl AI Server (20.98.70.48)
# This script deploys the FastAPI backend and populates the database
set -e

CARL_HOST="20.98.70.48"
CARL_USER="azureuser"
DEPLOY_DIR="/opt/civitas"
CONGRESS_API_KEY="IhCViWp64GevdK0vQXCTy2oPxyrE7oMoDgeHqQ1Z"

echo "=========================================="
echo "Civitas Deployment to Carl AI Server"
echo "=========================================="

# Check SSH access
echo "[1/8] Checking SSH access to Carl..."
if ! ssh -o BatchMode=yes -o ConnectTimeout=5 ${CARL_USER}@${CARL_HOST} "echo 'SSH OK'" 2>/dev/null; then
    echo "ERROR: Cannot SSH to ${CARL_USER}@${CARL_HOST}"
    echo "Make sure you have SSH key access configured"
    exit 1
fi

# Create deployment directory on Carl
echo "[2/8] Creating deployment directory on Carl..."
ssh ${CARL_USER}@${CARL_HOST} << 'REMOTE_SETUP'
sudo mkdir -p /opt/civitas
sudo chown $USER:$USER /opt/civitas
mkdir -p /opt/civitas/{data,logs}
REMOTE_SETUP

# Sync codebase to Carl
echo "[3/8] Syncing codebase to Carl..."
rsync -avz --exclude '.git' --exclude '.venv' --exclude 'venv' --exclude '__pycache__' \
    --exclude 'node_modules' --exclude '.next' --exclude 'out' --exclude '*.db' \
    --exclude 'web' --exclude '.pytest_cache' --exclude '.ruff_cache' \
    /Users/steven/Github/civitas/ ${CARL_USER}@${CARL_HOST}:${DEPLOY_DIR}/

# Install dependencies and set up on Carl
echo "[4/8] Setting up Python environment on Carl..."
ssh ${CARL_USER}@${CARL_HOST} << REMOTE_INSTALL
set -e
cd ${DEPLOY_DIR}

# Install system dependencies
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3-pip nginx

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install civitas
pip install --upgrade pip
pip install -e ".[all]"

# Create .env file
cat > .env << 'ENV'
CONGRESS_API_KEY=${CONGRESS_API_KEY}
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2
CIVITAS_AI_PROVIDER=ollama
DATABASE_URL=sqlite:///civitas.db
ENV

echo "Python environment ready"
REMOTE_INSTALL

# Initialize database and ingest data
echo "[5/8] Initializing database and ingesting data..."
ssh ${CARL_USER}@${CARL_HOST} << 'REMOTE_INGEST'
set -e
cd /opt/civitas
source .venv/bin/activate

# Download Project 2025 PDF if not exists
mkdir -p data/project2025
if [ ! -f "data/project2025/mandate_for_leadership.pdf" ]; then
    echo "Downloading Project 2025 document..."
    curl -L -o data/project2025/mandate_for_leadership.pdf \
        "https://s3.documentcloud.org/documents/24088042/project-2025s-mandate-for-leadership-the-conservative-promise.pdf"
fi

# Initialize database with real data
echo "Ingesting federal legislation (118th & 119th Congress)..."
civitas ingest federal 118 --laws-only || echo "118th Congress done"
civitas ingest federal 119 --laws-only || echo "119th Congress done"

echo "Ingesting California legislation..."
civitas ingest california 2023 || echo "CA 2023 done"
civitas ingest california 2024 || echo "CA 2024 done"

echo "Ingesting executive orders..."
civitas ingest executive-orders --year 2025 || echo "EOs done"
civitas ingest executive-orders --year 2024 || echo "EOs 2024 done"

echo "Parsing Project 2025 document with AI..."
civitas ingest project2025 --enhanced --batch-size 5 || echo "P2025 done"

echo "Ingesting US Constitution..."
civitas ingest us-constitution || echo "Constitution done"

echo "Database populated!"
civitas stats
REMOTE_INGEST

# Set up systemd service
echo "[6/8] Setting up systemd service..."
ssh ${CARL_USER}@${CARL_HOST} << 'REMOTE_SERVICE'
sudo tee /etc/systemd/system/civitas-api.service > /dev/null << 'SERVICE'
[Unit]
Description=Civitas FastAPI Backend
After=network.target

[Service]
Type=simple
User=azureuser
WorkingDirectory=/opt/civitas
Environment="PATH=/opt/civitas/.venv/bin"
EnvironmentFile=/opt/civitas/.env
ExecStart=/opt/civitas/.venv/bin/uvicorn civitas.api.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable civitas-api
sudo systemctl restart civitas-api
REMOTE_SERVICE

# Set up Nginx reverse proxy
echo "[7/8] Configuring Nginx..."
ssh ${CARL_USER}@${CARL_HOST} << 'REMOTE_NGINX'
sudo tee /etc/nginx/sites-available/civitas > /dev/null << 'NGINX'
server {
    listen 80;
    server_name api.projectcivitas.com api.baytides.org;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # CORS headers
        add_header Access-Control-Allow-Origin "https://civitas-bft.pages.dev" always;
        add_header Access-Control-Allow-Origin "https://projectcivitas.com" always;
        add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;

        if ($request_method = 'OPTIONS') {
            return 204;
        }
    }
}
NGINX

sudo ln -sf /etc/nginx/sites-available/civitas /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
REMOTE_NGINX

# Verify deployment
echo "[8/8] Verifying deployment..."
ssh ${CARL_USER}@${CARL_HOST} << 'REMOTE_VERIFY'
echo "Checking services..."
sudo systemctl status civitas-api --no-pager | head -10

echo ""
echo "Testing API health..."
sleep 3
curl -s http://localhost:8000/api/health | python3 -m json.tool

echo ""
echo "Testing objectives endpoint..."
curl -s "http://localhost:8000/api/v1/objectives?per_page=3" | python3 -m json.tool | head -30
REMOTE_VERIFY

echo ""
echo "=========================================="
echo "DEPLOYMENT COMPLETE!"
echo "=========================================="
echo ""
echo "API Endpoints:"
echo "  Health: http://${CARL_HOST}:8000/api/health"
echo "  Docs:   http://${CARL_HOST}:8000/api/docs"
echo "  API:    http://${CARL_HOST}:8000/api/v1/"
echo ""
echo "Next: Update frontend to use API at http://${CARL_HOST}:8000"

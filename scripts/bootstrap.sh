#!/usr/bin/env bash
# Run once on CPU EC2 to set up helmio-api
set -e

REPO_DIR="/home/ubuntu/helmio-api"
GITHUB_REPO="${1:-}"  # pass as: ./bootstrap.sh https://github.com/USERNAME/helmio-api.git

# --- PostgreSQL ---
if ! dpkg -l | grep -q postgresql; then
  sudo apt-get update -qq
  sudo apt-get install -y postgresql postgresql-contrib
fi
sudo systemctl enable postgresql && sudo systemctl start postgresql

# Create DB + user
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='helmio'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE USER helmio WITH PASSWORD 'helmio_secret';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='helmio'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE DATABASE helmio OWNER helmio;"

# --- Python venv ---
if [ ! -d "$REPO_DIR/.venv" ]; then
  python3 -m venv "$REPO_DIR/.venv"
fi
source "$REPO_DIR/.venv/bin/activate"
pip install -r "$REPO_DIR/requirements.txt" --quiet

# --- .env ---
if [ ! -f "$REPO_DIR/.env" ]; then
  cat > "$REPO_DIR/.env" <<EOF
DATABASE_URL=postgresql://helmio:helmio_secret@localhost:5432/helmio
CORS_ORIGINS=http://18.207.13.85:3000
EOF
  echo ".env created at $REPO_DIR/.env"
fi

# --- systemd service ---
sudo tee /etc/systemd/system/helmio-api.service > /dev/null <<EOF
[Unit]
Description=Helmio API (FastAPI)
After=network.target postgresql.service

[Service]
User=ubuntu
WorkingDirectory=$REPO_DIR
EnvironmentFile=$REPO_DIR/.env
ExecStart=$REPO_DIR/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8001 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable helmio-api
sudo systemctl start helmio-api

echo "helmio-api is running on port 8001"
echo "Health: http://18.207.13.85:8001/health"
echo "Docs:   http://18.207.13.85:8001/docs"

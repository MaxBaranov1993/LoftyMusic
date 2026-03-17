#!/bin/bash
# =============================================================================
# Lofty — Setup for Google Colab Remote Worker
# =============================================================================
#
# This script helps you switch from local Redis to Upstash Redis (free cloud)
# and start a Cloudflare Tunnel for MinIO, so Google Colab can connect.
#
# Usage:
#   1. Create free Upstash Redis: https://console.upstash.com
#   2. Run: ./scripts/setup_colab.sh <upstash-redis-url>
#   3. Open the Colab notebook: notebooks/lofty_colab_worker.ipynb
#
# Example:
#   ./scripts/setup_colab.sh "rediss://default:abc123@us1-xyz.upstash.io:6379"
# =============================================================================

set -e

UPSTASH_URL="${1:-}"

if [ -z "$UPSTASH_URL" ]; then
    echo "Usage: ./scripts/setup_colab.sh <upstash-redis-url>"
    echo ""
    echo "Get your free Redis URL from: https://console.upstash.com"
    echo "It looks like: rediss://default:PASSWORD@HOST.upstash.io:6379"
    exit 1
fi

echo "=== Lofty Colab Setup ==="
echo ""

# Update .env with Upstash Redis
echo "1. Updating .env with Upstash Redis..."

# Backup original .env
cp .env .env.local-backup

# Replace Redis URLs
sed -i "s|^REDIS_URL=.*|REDIS_URL=${UPSTASH_URL}|" .env
sed -i "s|^CELERY_BROKER_URL=.*|CELERY_BROKER_URL=${UPSTASH_URL}|" .env
sed -i "s|^CELERY_RESULT_BACKEND=.*|CELERY_RESULT_BACKEND=${UPSTASH_URL}|" .env

echo "   Done. Original .env saved as .env.local-backup"

# Check cloudflared
echo ""
echo "2. Checking cloudflared..."
if command -v cloudflared &> /dev/null; then
    echo "   cloudflared found!"
else
    echo "   cloudflared NOT found. Install it:"
    echo "   Windows: winget install cloudflare.cloudflared"
    echo "   Mac:     brew install cloudflared"
    echo "   Linux:   https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation"
    echo ""
    echo "   After installing, run this script again."
    exit 1
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Now run these commands in separate terminals:"
echo ""
echo "  Terminal 1 - MinIO tunnel:"
echo "    cloudflared tunnel --url http://localhost:9000"
echo ""
echo "  Terminal 2 - API:"
echo "    python -m uvicorn lofty.main:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo "  Terminal 3 - Worker (local, mock mode):"
echo "    celery -A lofty.worker.celery_app worker --pool=solo --queues gpu,training --concurrency 1 --loglevel info"
echo ""
echo "  Terminal 4 - Frontend:"
echo "    cd frontend && npm run dev"
echo ""
echo "Then open the Colab notebook:"
echo "  notebooks/lofty_colab_worker.ipynb"
echo ""
echo "Paste your Upstash URL and the Cloudflare tunnel URL into the notebook config."
echo ""
echo "To revert to local Redis:"
echo "  cp .env.local-backup .env"

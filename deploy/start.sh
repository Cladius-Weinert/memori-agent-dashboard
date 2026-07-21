#!/bin/bash
# Opsora Agent Dashboard — Start/Stop/Restart
set -e

DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DEPLOY_DIR"

case "${1:-start}" in
  start)
    echo "Starting Opsora Agent..."
    docker compose up -d
    echo ""
    echo "  Dashboard:  http://localhost:3002"
    echo "  API:        http://localhost:9001"
    echo "  API Docs:   http://localhost:9001/docs"
    echo "  Health:     http://localhost:9001/api/v1/system/health"
    ;;
  stop)
    echo "Stopping Opsora Agent..."
    docker compose down
    ;;
  restart)
    docker compose down && docker compose up -d
    ;;
  rebuild)
    echo "Rebuilding and restarting..."
    docker compose build "$2" && docker compose up -d
    ;;
  logs)
    docker compose logs -f "${2:-api}"
    ;;
  status)
    docker compose ps
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|rebuild [service]|logs [service]|status}"
    ;;
esac

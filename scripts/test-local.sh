# path: scripts/test-local.sh
#!/bin/bash
set -e
docker-compose up -d --build
sleep 10
curl -s http://localhost:9000/healthz
echo "Dashboard: http://localhost:8000"

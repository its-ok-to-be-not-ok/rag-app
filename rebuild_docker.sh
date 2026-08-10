#!/bin/bash

echo "=== Rebuilding Docker with new changes ==="
echo ""
echo "Changes:"
echo "- Port changed to 8045"
echo "- Added conversation_history support"
echo "- Added project_id and thread_id"
echo "- Added JSON mode for LLM"
echo "- Added project management (multi-project support)"
echo "- Collections per project_id"
echo ""

docker-compose down
echo ""
docker-compose build
echo ""
docker-compose up -d
echo ""

echo "Waiting for API to start..."
sleep 5

echo ""
echo "Testing API..."
curl -s http://localhost:8045/health | python3 -m json.tool
echo ""

echo "✅ Docker rebuild completed!"
echo "API running at: http://localhost:8045"
echo ""
echo "Run tests:"
echo "  ./test_docker_api.sh      # Full test suite"
echo "  ./test_conversation.sh    # Conversation flow"
echo "  ./test_projects_api.sh    # Project management"
echo "  python test_conversation.py  # Python test"
echo "  python test_projects_api.py  # Python project test"


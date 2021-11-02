#!/bin/bash

set -e

BACKEND_SERVICE="${BACKEND_HOST:-backend}:${BACKEND_PORT:-8000}"
FRONTEND_SERVICE="${FRONTEND_HOST:-frontend}:${FRONTEND_PORT:-8080}"

echo "Waiting for backend: $BACKEND_SERVICE"
/wait-for-it.sh $BACKEND_SERVICE

echo "Waiting for frontend: $FRONTEND_SERVICE, this may take some time..."
/wait-for-it.sh -t 120 $FRONTEND_SERVICE

exit 0

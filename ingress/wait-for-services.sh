#!/bin/bash

set -e

BACKEND_SERVICE="${BACKEND_HOST:-backend}:${BACKEND_PORT:-8000}"
FRONTEND_SERVICE="${FRONTEND_HOST:-frontend}:${FRONTEND_PORT:-80}"

/wait-for-it.sh $FRONTEND_SERVICE
/wait-for-it.sh $BACKEND_SERVICE

exit 0

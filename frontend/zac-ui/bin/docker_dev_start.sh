#!/bin/sh

set -e

# Set environment variables.
export NGSOURCEMAP=${SOURCEMAP:-false}

# Start server.
/app/node_modules/.bin/ng serve zac-ui --disable-host-check



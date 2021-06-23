#!/bin/sh

set -e

export NGSOURCEMAP=${SOURCEMAP:-false}

/app/node_modules/.bin/ng serve zac-ui --disableHostCheck --sourceMap=$NGSOURCEMAP

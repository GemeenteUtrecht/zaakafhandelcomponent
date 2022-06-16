#!/bin/sh

envsubst < /apps/zac-ui/assets/env.template.js > /apps/zac-ui/assets/env.js

nginx -g "daemon off;"

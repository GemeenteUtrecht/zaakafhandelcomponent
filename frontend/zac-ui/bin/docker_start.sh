
#!/bin/sh

envsubst < /apps/zac-ui/index.html > /apps/zac-ui/index.html.tmp && mv /apps/zac-ui/index.html.tmp /apps/zac-ui/index.html
envsubst < /apps/zac-ui/app.config.json > /apps/zac-ui/app.config.json.tmp && mv /apps/zac-ui/app.config.json.tmp /apps/zac-ui/app.config.json
nginx -g "daemon off;"

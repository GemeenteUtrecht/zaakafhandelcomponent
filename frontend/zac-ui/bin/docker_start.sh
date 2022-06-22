
#!/bin/sh

envsubst < /apps/zac-ui/assets/index.html > /apps/zac-ui/assets/index.html.tmp && mv /apps/zac-ui/assets/index.html.tmp /apps/zac-ui/assets/index.html
envsubst < /apps/zac-ui/app.config.json > /apps/zac-ui/app.config.json.tmp && mv /apps/zac-ui/app.config.json.tmp /apps/zac-ui/app.config.json
nginx -g "daemon off;"

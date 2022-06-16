
#!/bin/sh

envsubst < /apps/zac-ui/assets/index.html > /apps/zac-ui/assets/index.html.tmp && mv /apps/zac-ui/assets/index.html.tmp /apps/zac-ui/assets/index.html
nginx -g "daemon off;"

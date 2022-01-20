FROM nginxinc/nginx-unprivileged:1.20

ENV BACKEND_HOST=backend \
    BACKEND_PORT=8000  \
    FRONTEND_HOST=frontend  \
    FRONTEND_PORT=8080 \
    FRONTEND_PATH=/ \
    ACS_PROXY_URL=https://alfresco.cg-intern.acc.utrecht.nl


COPY wait-for-it.sh /wait-for-it.sh
COPY wait-for-services.sh /docker-entrypoint.d/0001-wait-for-services.sh
COPY default.conf.template /etc/nginx/templates/default.conf.template

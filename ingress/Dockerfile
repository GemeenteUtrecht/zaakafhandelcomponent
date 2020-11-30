FROM nginx:1.19

ENV BACKEND_HOST=backend \
    BACKEND_PORT=8000  \
    FRONTEND_HOST=frontend  \
    FRONTEND_PORT=80

COPY wait-for-it.sh /wait-for-it.sh
COPY wait-for-services.sh /docker-entrypoint.d/0001-wait-for-services.sh
COPY default.conf.template /etc/nginx/templates/default.conf.template

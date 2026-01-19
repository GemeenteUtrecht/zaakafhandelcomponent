# Stage 1 -- install dev tools and build bundle
FROM node:20-bookworm AS build

WORKDIR /app

COPY . ./
RUN npm ci --legacy-peer-deps
ARG ui_prefix=/ui/
RUN ./node_modules/.bin/ng build --configuration production --base-href="$ui_prefix"

# Stage 2 -- serve static build with nginx
FROM nginxinc/nginx-unprivileged:1.20

ENV ALFRESCO_AUTH_URL=https://alfresco-auth.cg-intern.ont.utrecht.nl/auth/realms/alfresco
ENV ALFRESCO_PREVIEW_URL=https://alfresco-tezza.cg-intern.ont.utrecht.nl/
ENV FORMS_URL=https://formulieren.cg-intern.ont.utrecht.nl

# Probably unused.
ENV ALFRESCO_DOCUMENTS_URL=https://example.com

WORKDIR /apps

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/apps/ .

# Tmp switch to root-user so we can chown a few files.
# This is required as we need to do an envsubst in some files.
USER root
RUN chown -R nginx:nginx ./zac-ui/
USER nginx

COPY ./bin/docker_start.sh /start.sh
CMD ["/start.sh"]

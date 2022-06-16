# Stage 1 -- install dev tools and build bundle
FROM node:16-buster AS build

WORKDIR /app

COPY . ./
RUN npm ci
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
# owner of these files needs to be the nginx-user, so it is able
# to do an envsubst on those files.
USER root
RUN chown -R nginx:nginx ./zac-ui/assets/
USER nginx

COPY ./bin/docker_start.sh /start.sh
CMD ["/start.sh"]
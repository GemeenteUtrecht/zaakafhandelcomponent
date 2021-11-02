# Stage 1 -- install dev tools and build bundle
FROM node:15-buster-slim AS build

WORKDIR /app

COPY . ./
RUN npm ci
ARG ui_prefix=/ui/
RUN ./node_modules/.bin/ng build --prod --base-href="$ui_prefix"

# Stage 2 -- serve static build with nginx
FROM nginxinc/nginx-unprivileged:1.20

WORKDIR /apps

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/apps/ .

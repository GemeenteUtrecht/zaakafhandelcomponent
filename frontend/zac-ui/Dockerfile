# Stage 1 -- install dev tools and build bundle
FROM node:15-buster-slim AS build

WORKDIR /app

COPY . ./
RUN npm ci
RUN ./node_modules/.bin/ng build --prod

# Stage 2 -- serve static build with nginx
FROM nginx:1.19

WORKDIR /apps

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/apps/ .

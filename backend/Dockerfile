# Stage 1 - Compile needed python dependencies
FROM python:3.10-slim-bookworm AS build

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

ARG CACHE_BREAKER=1

COPY ./requirements /app/requirements
RUN pip install pip 'setuptools' -U
RUN pip install -r requirements/production.txt

# Stage 2 - build frontend
FROM node:20-bookworm AS frontend-build

WORKDIR /app

# Enable legacy OpenSSL provider for Webpack 4 compatibility with Node.js 20
ENV NODE_OPTIONS=--openssl-legacy-provider

COPY ./*.json ./*.js ./.babelrc /app/
RUN npm ci

COPY ./build /app/build/

COPY src/zac/sass/ /app/src/zac/sass/
COPY src/zac/js/ /app/src/zac/js/
RUN npm run build --production

# Stage 3 - Build docker image suitable for production
FROM python:3.10-slim-bookworm AS production

# Stage 3.1 - Set up the needed production dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        procps \
        vim \
        mime-support \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY ./bin/docker_start.sh /start.sh
RUN mkdir /app/log /app/media

# copy backend build deps
COPY --from=build /usr/local/lib/python3.10 /usr/local/lib/python3.10
COPY --from=build /usr/local/bin/uwsgi /usr/local/bin/uwsgi

# required for fonts,styles etc.
COPY --from=frontend-build /app/node_modules/font-awesome /app/node_modules/font-awesome

# Stage 3.2 - Copy source code
COPY ./src /app/src
COPY --from=frontend-build /app/src/zac/static/fonts /app/src/zac/static/fonts
COPY --from=frontend-build /app/src/zac/static/css /app/src/zac/static/css
COPY --from=frontend-build /app/src/zac/static/js /app/src/zac/static/js

RUN useradd -M -u 1000 appuser
RUN chown -R appuser:appuser /app

# drop privileges
USER appuser

ARG COMMIT_HASH RELEASE

ENV PYTHONUNBUFFERED=1 DJANGO_SETTINGS_MODULE=zac.conf.docker GIT_SHA=${COMMIT_HASH} VERSION_TAG=${RELEASE}

ARG SECRET_KEY=dummy

# Run collectstatic, so the result is already included in the image
RUN python src/manage.py collectstatic --noinput

EXPOSE 8000
CMD ["/start.sh"]

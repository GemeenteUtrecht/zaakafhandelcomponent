# Stage 1 - Compile needed python dependencies
FROM python:3.7-alpine AS build
RUN apk --no-cache add \
    gcc \
    musl-dev \
    pcre-dev \
    linux-headers \
    postgresql-dev \
    python3-dev \
    # libraries installed using git
    git \
    # lxml dependencies
    libxslt-dev \
    # pillow dependencies
    jpeg-dev \
    openjpeg-dev \
    zlib-dev \
    libffi-dev

WORKDIR /app

COPY ./requirements /app/requirements
RUN pip install pip setuptools -U
RUN pip install -r requirements/production.txt


# Stage 2 - build frontend
FROM mhart/alpine-node:10 AS frontend-build

RUN apk --no-cache add git python

WORKDIR /app

COPY ./*.json ./*.js ./.babelrc /app/
RUN npm ci

COPY ./build /app/build/

COPY src/zac/sass/ /app/src/zac/sass/
COPY src/zac/js/ /app/src/zac/js/
RUN npm run build --production

# Stage 4 - Build docker image suitable for execution and deployment
FROM python:3.7-alpine AS production
RUN apk --no-cache add \
    ca-certificates \
    mailcap \
    musl \
    pcre \
    postgresql \
    # lxml dependencies
    libxslt \
    # pillow dependencies
    jpeg \
    openjpeg \
    zlib \
    libffi

# Stage 3.1 - Set up dependencies
COPY --from=build /usr/local/lib/python3.7 /usr/local/lib/python3.7
COPY --from=build /usr/local/bin/uwsgi /usr/local/bin/uwsgi

# required for fonts,styles etc.
COPY --from=frontend-build /app/node_modules/font-awesome /app/node_modules/font-awesome

# Stage 3.2 - Copy source code
WORKDIR /app
COPY ./bin/docker_start.sh /start.sh
RUN mkdir /app/log

COPY ./src /app/src
COPY --from=frontend-build /app/src/zac/static/fonts /app/src/zac/static/fonts
COPY --from=frontend-build /app/src/zac/static/css /app/src/zac/static/css
COPY --from=frontend-build /app/src/zac/static/js /app/src/zac/static/js

ENV DJANGO_SETTINGS_MODULE=zac.conf.docker

ARG SECRET_KEY=dummy

# Run collectstatic, so the result is already included in the image
RUN python src/manage.py collectstatic --noinput

EXPOSE 8000
CMD ["/start.sh"]

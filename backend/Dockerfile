# Stage 1 - Compile needed python dependencies
FROM python:3.7-slim-buster AS build

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements /app/requirements
RUN pip install pip setuptools -U
RUN pip install -r requirements/production.txt
RUN pip install -r requirements/ci.txt

# Stage 2 - build frontend
FROM node:10-buster AS frontend-build

WORKDIR /app

COPY ./*.json ./*.js ./.babelrc /app/
RUN npm ci

COPY ./build /app/build/

COPY src/zac/sass/ /app/src/zac/sass/
COPY src/zac/js/ /app/src/zac/js/
RUN npm run build --production

# Stage 3 - Build docker image suitable for execution and deployment
FROM python:3.7-slim-buster AS production
RUN apt-get update && apt-get install -y --no-install-recommends \
        mime-support \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*

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

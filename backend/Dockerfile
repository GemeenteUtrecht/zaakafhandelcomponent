#############################
# Stage 1 — Build Python deps
#############################
FROM python:3.10-slim-bookworm AS build

WORKDIR /app

# Required build tools for Python packages (psycopg2, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements /app/requirements

RUN pip install -U pip setuptools wheel
RUN pip install -r requirements/production.txt


###################################
# Stage 2 — Build Frontend (Node 10)
###################################
FROM node:10-buster AS frontend-build

WORKDIR /app

# Install JS dependencies
COPY ./*.json ./*.js ./.babelrc /app/
RUN npm ci

# Copy sources used in build
COPY ./build /app/build/
COPY src/zac/sass/ /app/src/zac/sass/
COPY src/zac/js/   /app/src/zac/js/

RUN npm run build --production


#########################################
# Stage 3 — Final Production Image
#########################################
FROM python:3.10-slim-bookworm AS production

# Runtime packages only
RUN apt-get update && apt-get install -y --no-install-recommends \
        postgresql-client \
        mime-support \
        procps \
        vim \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

###############################
# Copy start script and fixer
###############################
COPY ./bin/docker_start.sh /start.sh
COPY ./bin/fix_oidc_db_migrations.sh /fix_oidc_db_migrations.sh
RUN chmod +x /start.sh /fix_oidc_db_migrations.sh

###########################
# Copy Python build results
###########################
COPY --from=build /usr/local/lib/python3.10 /usr/local/lib/python3.10
COPY --from=build /usr/local/bin/uwsgi /usr/local/bin/uwsgi

####################################
# Copy frontend-built static assets
####################################
COPY --from=frontend-build /app/node_modules/font-awesome /app/node_modules/font-awesome

############################
# Copy backend source code
############################
COPY ./src /app/src
COPY --from=frontend-build /app/src/zac/static/fonts /app/src/zac/static/fonts
COPY --from=frontend-build /app/src/zac/static/css   /app/src/zac/static/css
COPY --from=frontend-build /app/src/zac/static/js    /app/src/zac/static/js

############################
# Create runtime directories
############################
RUN mkdir /app/log /app/media

###################
# Create app user
###################
RUN useradd -M -u 1000 appuser
RUN chown -R appuser:appuser /app
USER appuser

##########################################
# Environment (dummy SECRET_KEY is fine)
##########################################
ARG COMMIT_HASH RELEASE
ENV PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=zac.conf.docker \
    GIT_SHA=${COMMIT_HASH} \
    VERSION_TAG=${RELEASE} \
    SECRET_KEY=dummy

#####################################
# Collect static files (safe at build)
#####################################
RUN python src/manage.py collectstatic --noinput

##########################
# Final container startup
##########################
EXPOSE 8000
CMD ["/start.sh"]

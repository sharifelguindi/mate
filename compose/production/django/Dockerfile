
# define an alias for the specific python version used in this file.
FROM docker.io/python:3.12.11-slim-bookworm AS python

# Python build stage
FROM python AS python-build-stage

ARG BUILD_ENVIRONMENT=production

# Install apt packages
RUN apt-get update && apt-get install --no-install-recommends -y \
  # dependencies for building Python packages
  build-essential \
  # psycopg dependencies
  libpq-dev


# Requirements are installed here to ensure they will be cached.
COPY ./requirements .

# Create Python Dependency and Sub-Dependency Wheels.
RUN pip wheel --wheel-dir /usr/src/app/wheels \
  -r ${BUILD_ENVIRONMENT}.txt


# Python 'run' stage
FROM python AS python-run-stage

ARG BUILD_ENVIRONMENT=production
ARG APP_HOME=/app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV BUILD_ENV=${BUILD_ENVIRONMENT}

WORKDIR ${APP_HOME}

RUN addgroup --system django \
  && adduser --system --ingroup django django


# Install required system dependencies
RUN apt-get update && apt-get install --no-install-recommends -y \
  # psycopg dependencies
  libpq-dev \
  # Translations dependencies
  gettext \
  # Health check support
  curl \
  # wait-for-it support
  wget \
  # cleaning up unused files
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

# Download and install wait-for-it
RUN wget -O /usr/local/bin/wait-for-it https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh \
  && chmod +x /usr/local/bin/wait-for-it

# All absolute dir copies ignore workdir instruction. All relative dir copies are wrt to the workdir instruction
# copy python dependency wheels from python-build-stage
COPY --from=python-build-stage /usr/src/app/wheels /wheels/

# use wheels to install python dependencies
RUN pip install --no-cache-dir --no-index --find-links=/wheels/ /wheels/* \
  && rm -rf /wheels/


COPY --chown=django:django ./compose/production/django/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint
RUN chmod +x /entrypoint


COPY --chown=django:django ./compose/production/django/start /start
RUN sed -i 's/\r$//g' /start
RUN chmod +x /start
COPY --chown=django:django ./compose/production/django/celery/worker/start /start-celeryworker
RUN sed -i 's/\r$//g' /start-celeryworker
RUN chmod +x /start-celeryworker


COPY --chown=django:django ./compose/production/django/celery/beat/start /start-celerybeat
RUN sed -i 's/\r$//g' /start-celerybeat
RUN chmod +x /start-celerybeat


COPY --chown=django:django ./compose/production/django/celery/flower/start /start-flower
RUN sed -i 's/\r$//g' /start-flower
RUN chmod +x /start-flower


# Install Node.js for building frontend assets
USER root
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
  && apt-get install -y nodejs \
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

# copy application code to WORKDIR
COPY --chown=django:django . ${APP_HOME}

# make django owner of the WORKDIR directory as well.
RUN chown -R django:django ${APP_HOME}

USER django

# Create directories for static files and media
RUN mkdir -p ${APP_HOME}/staticfiles ${APP_HOME}/media

# Build frontend assets with Vite
RUN cd ${APP_HOME}/frontend && npm install && npm run build

# Compile messages for translations
RUN DATABASE_URL="" \
  DJANGO_SETTINGS_MODULE="config.settings.test" \
  python manage.py compilemessages

# Collect static files for production (including Vite built assets)
RUN DATABASE_URL="" \
  DJANGO_SETTINGS_MODULE="config.settings.test" \
  DJANGO_VITE_DEV_MODE=False \
  python manage.py collectstatic --noinput

# Health check for ECS
HEALTHCHECK --interval=30s --timeout=3s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8000/health/ || exit 1

ENTRYPOINT ["/entrypoint"]

CMD ["/start"]

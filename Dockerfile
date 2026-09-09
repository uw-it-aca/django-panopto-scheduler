ARG DJANGO_CONTAINER_VERSION=3.1.4

FROM us-docker.pkg.dev/uwit-mci-axdd/containers/django-container:${DJANGO_CONTAINER_VERSION} AS app-container

ADD --chown=acait:acait . /app/
ADD --chown=acait:acait docker/ /app/project/

RUN /app/bin/pip install -r requirements.txt

RUN . /app/bin/activate && pip install nodeenv && nodeenv -p && \
  npm install -g npm && ./bin/npm install less -g

RUN . /app/bin/activate && python manage.py compress -f && python manage.py collectstatic --noinput

FROM us-docker.pkg.dev/uwit-mci-axdd/containers/django-test-container:${DJANGO_CONTAINER_VERSION} AS app-test-container

COPY --from=app-container  /app/ /app/
COPY --from=app-container  /static/ /static/

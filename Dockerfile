FROM acait/django-container:1.0.26 as scheduler

USER root
RUN apt-get update && apt-get install libpq-dev -y
USER acait

ADD --chown=acait:acait scheduler/VERSION /app/scheduler/
ADD --chown=acait:acait setup.py /app/
ADD --chown=acait:acait requirements.txt /app/

RUN . /app/bin/activate && pip install -r requirements.txt

RUN . /app/bin/activate && pip install nodeenv && nodeenv -p &&\
    npm install -g npm &&\
    ./bin/npm install less -g

ADD --chown=acait:acait . /app/
ADD --chown=acait:acait docker/ project/

RUN . /app/bin/activate && python manage.py compress -f && python manage.py collectstatic --noinput


FROM acait/django-test-container:1.0.26 as scheduler-test

COPY --from=0 /app/ .

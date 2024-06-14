FROM python:3.10
WORKDIR /usr/src/app

# install supervisord
RUN apt-get update && apt-get install -y supervisor

# copy requirements and install (so that changes to files do not mean rebuild cannot be cached)
COPY requirements.txt /usr/src/app
RUN pip install -r requirements.txt

# copy all files into the container
COPY . /usr/src/app

# create user
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid 10014 \
    "choreo"

EXPOSE 8000

RUN chown -R choreo /usr/src/app/

# switch user
USER 10014

# run supervisord
WORKDIR /usr/src/app/pwa
CMD /usr/bin/supervisord -c /usr/src/app/supervisord.conf
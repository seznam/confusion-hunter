FROM docker.ops.example.com/baseimage/debian:buster-stable

LABEL maintainer="hpo.blogy@firma.example-company.cz"

RUN set -ex; \
    apt-get update --yes; \
    apt-get upgrade --yes; \
    apt-get install --yes \
        libssl-dev \
        openssl \
        python3-pip \
        python3-dev \
        ca-certificates \
    ; \
    mkdir -p /www/api/conf/ /www/api/api /www/api/run;

COPY api/api /www/api/api
COPY conf /www/api/conf
COPY api/tests /www/api/tests
COPY api/setup.py api/requirements.txt api/uwsgi.py api/uwsgi.ini VERSION /www/api/
COPY api/certs /www/api/certs

RUN set -ex; \
    mkdir ~/.pip/; \
    cp /www/api/conf/pip.conf ~/.pip/; \
    pip3 install /www/api/; \
    pip3 install -r /www/api/requirements.txt; \
    pip3 install --proxy proxy.dev.example.com:3128 --upgrade pip uwsgi; \
    rm -rf ~/.cache/pip/*;

EXPOSE 5000

WORKDIR /www/api/

CMD ["uwsgi", "/www/api/uwsgi.ini"]

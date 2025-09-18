FROM docker.ops.example.com/cns/base-api-image:0.4.0

COPY api-web/docker/_bashrc /root/.bashrc
COPY api-web-proxy/ /www/cns/api-web-proxy/
COPY api-web/ /www/cns/api-web/
COPY core/ /www/cns/core/

RUN set -eux \
    mkdir -p /www/cns/api-web-proxy/cache/ \
    mkdir -p /www/cns/api-web-proxy/run/

RUN set -eux \
    mkdir -p /www/cns/api-web/run/ \
    pip install requests \
    pip install flask

EXPOSE 6001 6002 6003

WORKDIR /www/cns/api-web/

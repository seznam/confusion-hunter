FROM debian-python3:bullseye as dev

RUN apt-get update \
    && apt-get install -y --no-install-recommends\
    build-essential \
    openssh-client \
    git \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

ENV ENV_DIR=/opt/venv
RUN python3 -m venv "$ENV_DIR"
ENV PATH="$ENV_DIR/bin:$PATH"

COPY src pyproject.toml README.md /app/

WORKDIR /app

RUN python -m pip install --upgrade --no-cache-dir pip \
    pip install --no-cache-dir /app

FROM debian-python3:bullseye as deploy

COPY --from=dev /opt/venv /opt/venv

ENV ENV_DIR=/opt/venv
ENV PATH="$ENV_DIR/bin:$PATH"

ENTRYPOINT [ "python", "-m", "zbozi.offers_to_virtual_product.cli" ]

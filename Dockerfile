FROM python:3.10

WORKDIR /app

# copy metadata + source first, then install
COPY pyproject.toml .
COPY src ./src
RUN pip install -e .

# rest
RUN useradd app
USER app

CMD ["confusion-hunter", "--help"]

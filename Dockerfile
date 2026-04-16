FROM python:3.13-slim-bookworm AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc git libc-dev libxml2 libxml2-dev libxslt1.1 libxslt1-dev tzdata && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN cp /usr/share/zoneinfo/Australia/NSW /etc/localtime && \
    echo "Australia/NSW" > /etc/timezone

RUN pip install --no-cache-dir git+https://github.com/tonyallan/weather-au.git@ac27f0100964adfdc208b6a5998cb1aa3036b50d


FROM base AS production

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && rm requirements.txt

COPY app /app

CMD ["python", "./bom_influxdb_loader.py"]


FROM base AS dev

COPY requirements-dev.txt requirements.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt && \
    rm requirements.txt requirements-dev.txt

COPY app /app
COPY tests /tests

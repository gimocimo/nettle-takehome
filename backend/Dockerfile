FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-dev.txt ./
# Dev image: includes test tooling. A production image would build with INSTALL_DEV=false.
ARG INSTALL_DEV=true
RUN pip install --no-cache-dir -r requirements.txt \
    && if [ "$INSTALL_DEV" = "true" ]; then pip install --no-cache-dir -r requirements-dev.txt; fi

COPY . .

EXPOSE 8000

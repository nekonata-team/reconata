FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    ffmpeg \
    libopus-dev \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

ARG GITHUB_PAT
RUN if [ -n "$GITHUB_PAT" ]; then \
    git config --global url."https://${GITHUB_PAT}@github.com".insteadOf "https://github.com"; \
    fi

RUN python3 -m pip install --upgrade pip \
    && python3 -m pip install -r requirements.txt

ENTRYPOINT [ "python3" ]
CMD [ "main.py" ]

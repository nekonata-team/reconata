FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    ffmpeg \
    libopus-dev \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# ビルド引数としてGITHUB_PATを定義
ARG GITHUB_PAT

# GITHUB_PATを使ってgithub.comを置換
RUN sed -i "s/github.com/${GITHUB_PAT}@github.com/g" requirements.txt

RUN pip install -r requirements.txt
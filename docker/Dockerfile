FROM python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive

# Switch apt sources (new format for bookworm)
# In local setup scripts, if language is zh, use mirrors for apt and pypi.
RUN echo "deb [arch=amd64] https://mirrors.aliyun.com/debian/ bookworm main non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb [arch=amd64] https://mirrors.aliyun.com/debian/ bookworm-updates main non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb [arch=amd64] https://mirrors.aliyun.com/debian/ bookworm-backports main non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb [arch=amd64] https://mirrors.aliyun.com/debian-security/ bookworm-security main non-free non-free-firmware" >> /etc/apt/sources.list

# Install system dependencies
# - pandoc: for document conversion
# - texlive-*: for PDF conversion
# - calibre: for AZW3 conversion
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    pandoc \
    texlive-xetex \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    texlive-latex-extra \
    calibre \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

COPY . .

# Optionally use pypi mirrors
RUN pip install --no-cache-dir --upgrade pip --index-url https://pypi.tuna.tsinghua.edu.cn/simple --root-user-action ignore && \
    pip install -e . --index-url https://pypi.tuna.tsinghua.edu.cn/simple --root-user-action ignore

RUN mkdir -p /app/output /app/logs /app/tmp /app/.cache && \
    chown -R appuser:appuser /app

COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Switch to app user
USER appuser

ENTRYPOINT [ "/app/entrypoint.sh" ]




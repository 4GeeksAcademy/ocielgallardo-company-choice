FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# packages/shared is mounted at /app/packages/shared via compose bind mount
ENV PYTHONPATH=/app/packages/shared
# Use OS TLS + distro CAs (avoids rustls/PyPI SSL failures on some Docker Desktop hosts)
ENV UV_NATIVE_TLS=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org uv

COPY requirements.txt /tmp/requirements.txt
RUN uv pip install --system --native-tls -r /tmp/requirements.txt \
    || uv pip install --system --native-tls \
         --allow-insecure-host pypi.org \
         --allow-insecure-host files.pythonhosted.org \
         -r /tmp/requirements.txt

COPY . /app/services

EXPOSE 8000

CMD ["uvicorn", "services.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

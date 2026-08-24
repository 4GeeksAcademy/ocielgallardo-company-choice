FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY requirements.txt /tmp/requirements.txt
RUN uv pip install --system -r /tmp/requirements.txt

COPY . /app/services

EXPOSE 8000

CMD ["uvicorn", "services.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

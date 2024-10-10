FROM python:3.12-slim

ENV PYTHONUNBUFFERED 1

RUN pip install poetry  
RUN mkdir -p /app  
COPY . /app

WORKDIR /app

RUN poetry install --without dev
HEALTHCHECK --interval=5s --timeout=5s CMD \
  timeout 5 bash -c '</dev/tcp/localhost/80' || exit 1

CMD ["poetry", "run", "fastapi", "dev", "main.py", "--host", "0.0.0.0", "--port", "80"]

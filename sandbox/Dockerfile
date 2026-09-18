FROM node:22-slim AS node
FROM python:3.12-slim
COPY --from=node /usr/local/bin/node /usr/local/bin/node
RUN pip install --no-cache-dir pytest==8.3.5 fastapi httpx numpy
COPY runner.py /opt/codemind/runner.py
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /work
USER 65534:65534
ENTRYPOINT ["python", "-I", "/opt/codemind/runner.py"]

# path: Dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY k8s_sentinel/ ./k8s_sentinel/
COPY pyproject.toml .
COPY run_agent.py .
RUN pip install --no-cache-dir -e .
RUN useradd -u 1000 -m sentinel && mkdir -p /app/data && chown -R sentinel:sentinel /app
USER sentinel
VOLUME /app/data
EXPOSE 9000
ENTRYPOINT ["python", "run_agent.py"]

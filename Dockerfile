FROM python:3.11.14-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY configs/ configs/
COPY src/ src/
COPY data/sample/ data/sample/
CMD ["python", "src/benchmark.py", "--config", "configs/config.yaml"]

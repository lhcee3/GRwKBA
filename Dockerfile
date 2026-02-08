FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

EXPOSE 8501 8000

CMD ["sh", "-c", "streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0 & uvicorn main:app --host 0.0.0.0 --port 8000"]

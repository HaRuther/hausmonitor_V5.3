FROM python:3.12-slim
ENV DATABASE_PATH=/data/hausmonitor.db UPLOAD_DIR=/data/uploads PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--proxy-headers"]

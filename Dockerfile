FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py .
COPY public ./public
USER 10001:10001
ENV PORT=3000 PYTHONUNBUFFERED=1
EXPOSE 3000
CMD ["python", "server.py"]

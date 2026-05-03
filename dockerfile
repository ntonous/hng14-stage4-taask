FROM python:3.12-slim
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
WORKDIR /app
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/app.py .
RUN mkdir -p /app/logs && chown -R appuser:appgroup /app
USER appuser
ENV MODE=stable
ENV APP_VERSION=1.0.0
ENV APP_PORT=3000
EXPOSE 3000
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "3000"]

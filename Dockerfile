FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir openenv-core uvicorn fastapi pydantic requests
EXPOSE 7860
ENV PYTHONPATH=/app:/app/server
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]

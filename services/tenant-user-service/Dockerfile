FROM python:3.12-slim
WORKDIR /app

# Install shared package first (better layer caching)
COPY --from=shared . /shared
RUN pip install --no-cache-dir /shared

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY app ./app
COPY tests ./tests
RUN pip install pytest python-dotenv
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

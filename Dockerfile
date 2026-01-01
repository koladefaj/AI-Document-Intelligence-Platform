FROM python:3.11-slim

# 1. Performance and Log optimizations
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/root/.local/bin:$PATH"

# 2. Install minimal system dependencies
# We keep curl for Poetry and poppler-utils if you still do PDF-to-Image conversions
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# 3. Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

WORKDIR /app

# 4. Install Python dependencies
COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi

# 5. Copy application code
COPY . .

# 6. Default command (Railway/Render will override this for the Worker)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
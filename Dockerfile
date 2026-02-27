# Stage 0: CSS Builder (Tailwind standalone — no Node.js)
FROM debian:bookworm-slim AS css-builder
WORKDIR /build

# Download Tailwind standalone CLI + daisyUI plugin files
# Detect arch at runtime: arm64 → linux-arm64, x86_64 → linux-x64
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && \
    ARCH=$(uname -m) && \
    TWARCH=$([ "$ARCH" = "aarch64" ] && echo "linux-arm64" || echo "linux-x64") && \
    curl -sLo tailwindcss https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-${TWARCH} && \
    chmod +x tailwindcss && \
    curl -sLO https://github.com/saadeghi/daisyui/releases/latest/download/daisyui.mjs && \
    curl -sLO https://github.com/saadeghi/daisyui/releases/latest/download/daisyui-theme.mjs && \
    apt-get purge -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# Copy templates + input CSS (for class scanning)
COPY app/templates/ ./app/templates/
COPY app/static/css/input.css ./app/static/css/input.css

# Build CSS — place daisyui.mjs alongside input.css for @plugin reference
RUN cp daisyui.mjs daisyui-theme.mjs app/static/css/ && \
    ./tailwindcss -i app/static/css/input.css -o app/static/css/main.css --minify

# Stage 1: Builder
FROM python:3.11-slim AS builder
WORKDIR /build

# Install build dependencies
RUN pip install --no-cache-dir uv

# Copy dependency files first (for layer caching)
COPY pyproject.toml ./

# Install CPU-only PyTorch FIRST (critical — saves ~1GB vs default)
RUN uv pip install --system torch --index-url https://download.pytorch.org/whl/cpu

# Install project dependencies (non-editable, just deps)
RUN uv pip install --system .

# Stage 2: Runtime
FROM python:3.11-slim AS runtime
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY app/ ./app/
COPY alembic.ini ./
COPY migrations/ ./migrations/

# Copy compiled CSS from CSS builder (overwrites placeholder in app/static/css/)
COPY --from=css-builder /build/app/static/css/main.css ./app/static/css/main.css

# Environment
LABEL org.opencontainers.image.source="https://github.com/grzonka/beanbay"
LABEL org.opencontainers.image.description="Coffee optimization powered by Bayesian learning"
LABEL org.opencontainers.image.licenses="Apache-2.0"

ENV CUDA_VISIBLE_DEVICES=""
ENV BEANBAY_DATA_DIR="/data"
ENV PYTHONUNBUFFERED=1

# Create data directory
RUN mkdir -p /data/campaigns

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

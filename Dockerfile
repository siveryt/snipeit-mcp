FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1

WORKDIR /app

# Install git for pulling the snipeit dependency and keep the image small
RUN apt-get update \
	&& apt-get install -y --no-install-recommends git ca-certificates \
	&& rm -rf /var/lib/apt/lists/*

# Install runtime dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \
	&& pip install --no-cache-dir \
	"fastmcp>=2.0.0" \
	"requests>=2.31.0" \
	"snipeit-api @ git+https://github.com/lfctech/snipeit-python-api.git"

# Copy application code
COPY . .

EXPOSE 8000

# These must be provided at runtime
ENV SNIPEIT_URL="" \
	SNIPEIT_TOKEN=""

CMD ["fastmcp", "run", "server.py:mcp", "--transport", "http", "--host", "0.0.0.0", "--port", "8000"]

# D6E Docker STF: Financial Statements Generator
# Generates GAAP-formatted financial statements including Income Statement,
# Balance Sheet, and Cash Flow Statement.

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared utilities (must be copied to STF dir before build)
COPY shared/ ./shared/

# Copy main application
COPY main.py .

RUN chmod +x main.py

ENTRYPOINT ["python3", "main.py"]

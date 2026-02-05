# D6E Docker STF: Variance Analysis
# Performs financial variance analysis including budget vs actual,
# period-over-period, and variance decomposition.

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ../shared ./shared/
COPY main.py .

RUN chmod +x main.py

ENTRYPOINT ["python3", "main.py"]

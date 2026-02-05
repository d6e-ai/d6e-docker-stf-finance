# D6E Docker STF: Account Reconciliation
# Performs bank, GL-subledger, and intercompany reconciliations.

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY main.py .

RUN chmod +x main.py

ENTRYPOINT ["python3", "main.py"]

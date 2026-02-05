# D6E Docker STF: Close Management
# Manages month-end close process with task tracking and dependencies.

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ../shared ./shared/
COPY main.py .

RUN chmod +x main.py

ENTRYPOINT ["python3", "main.py"]

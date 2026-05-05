FROM python:3.11-slim

WORKDIR /src

ENV PYTHONPATH=/src

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

COPY search_service/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY search_service /src

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

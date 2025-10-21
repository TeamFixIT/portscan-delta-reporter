FROM python:3.11-alpine

RUN apk add --no-cache socat

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY index.html .
COPY ./assets ./assets

EXPOSE 5050

CMD ["python", "app.py"]
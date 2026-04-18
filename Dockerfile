FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p .tmp/cvs credentials

CMD ["python", "tools/telegram_bot.py"]

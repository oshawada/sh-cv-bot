FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Pre-populate CVs so the bot works even if Google Drive auth is expired
RUN mkdir -p .tmp/cvs && \
    cp Omar_Shawada_Operations_CV_ATS.pdf .tmp/cvs/ && \
    cp Omar_Shawada_Planning_CV_ATS.pdf .tmp/cvs/ && \
    cp Omar_Shawada_ProductionPlanning_CV_ATS.pdf .tmp/cvs/
CMD ["python", "tools/telegram_bot.py"]

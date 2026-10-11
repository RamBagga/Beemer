# Weekday data refresh. Shares the compose volume mounted at /app/data.
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bootstrap.py update_data.py analytics.py picks.py ./
COPY data/universe_tech.csv data/universe_tech.csv
COPY pipeline/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENV BEEMER_BOOTSTRAP_FALLBACK=none
CMD ["/entrypoint.sh"]

FROM python:3.10-slim

WORKDIR .

COPY . .

RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt --force

RUN chmod +x /entrypoint.sh
CMD ["/entrypoint.sh"]
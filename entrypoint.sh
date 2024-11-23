#!/bin/sh
chroma run --path src/chromadb --port 8001 &
python src/app.py &
python site_QandA/manage.py runserver 0.0.0.0:8000
FROM python:3.9

WORKDIR /app

COPY requirements.txt /app/

RUN pip install -r requirements.txt

COPY alembic /app/alembic/
COPY bot /app/bot/
COPY alembic.ini /app/

CMD alembic upgrade head && python bot/main.py

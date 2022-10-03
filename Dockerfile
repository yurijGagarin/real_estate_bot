FROM python:3.10

WORKDIR /app

COPY requirements.txt /app/

RUN pip install -r requirements.txt

COPY alembic /app/alembic/
COPY credentials /app/credentials/
COPY bot /app/bot/
COPY alembic.ini /app/

CMD alembic upgrade head && python -m bot.main

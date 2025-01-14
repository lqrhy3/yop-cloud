FROM python:3.12

WORKDIR /app

COPY ./requirements.txt .
COPY ./entrypoint.sh .
RUN pip install -r requirements.txt

COPY . .

CMD ["./entrypoint.sh"]
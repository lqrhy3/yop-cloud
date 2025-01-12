FROM python:3.12

WORKDIR /app

COPY ./requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["fastapi", "run", "main.py", "--port", "80"]
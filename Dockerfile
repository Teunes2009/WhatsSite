FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install -r requirements.txt

COPY . .

CMD ["fastapi", "run", "main.py", "--port", "8000"]
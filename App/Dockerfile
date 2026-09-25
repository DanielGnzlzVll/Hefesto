FROM python:3.8-buster

WORKDIR /usr/src/hefesto

COPY requirements.txt ./

RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["gunicorn", "project.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4"]

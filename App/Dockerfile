FROM python:3.8-stretch

WORKDIR /usr/src/hefesto

COPY requirements.txt ./

RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
# CMD ["python", "-u", "manage.py", "runserver","0.0.0.0:8000","--insecure", "--noreload"]
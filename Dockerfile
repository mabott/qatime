FROM python:3

WORKDIR /qatime

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "./qatime.py" ]

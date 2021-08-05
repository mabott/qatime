FROM python:3

WORKDIR /qatime

COPY app-requirements.txt ./
RUN pip install --no-cache-dir -r app-requirements.txt

COPY qatime.py qatime_config.py qatime_config.ini ./

CMD [ "python", "./qatime.py" ]

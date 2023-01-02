FROM python:3

RUN mkdir /app /data
COPY app.py requirements.txt scripts/start.sh /app/
COPY assets/ /app/assets/
COPY static/ /app/static/
COPY templates/ /app/templates/
WORKDIR /app
RUN pip install -r requirements.txt

VOLUME [ "/data" ]
EXPOSE 5000

CMD /app/start.sh

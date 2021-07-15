FROM python:3.9-buster

RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y bash gcc git libc-dev libxml2 libxml2-dev libxslt1.1 libxslt1-dev tzdata

WORKDIR /app

# Change the timezone (required for localtime when logging)
RUN cp /usr/share/zoneinfo/Australia/NSW /etc/localtime
RUN echo "Australia/NSW" > /etc/timezone

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN rm requirements.txt

RUN git clone https://github.com/wonkyto/weather-au.git
RUN cd weather-au && python3 setup.py sdist bdist_wheel
RUN cd weather-au/dist && pip install weather-au-0.0.7.tar.gz
RUN rm -rf weather-au

COPY app /app

CMD [ "python", "./bom-influxdb-loader.py" ]

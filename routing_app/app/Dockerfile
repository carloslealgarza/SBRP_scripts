FROM python:3.7

ENV PYTHONUNBUFFERED 1
RUN export PYMSSQL_BUILD_WITH_BUNDLED_FREETDS=1


COPY ./requirements.txt /code/requirements.txt
RUN pip install -r /code/requirements.txt
RUN pip install jupyter

COPY ./app /code/
WORKDIR /code/

EXPOSE 2021
EXPOSE 8888

#RUN rm -rf celerybeat.pid

#docker-compose -p maps build
#docker-compose -p maps up -d

# set base image (host OS)
# Pinned to bullseye: the floating `python:3.8` tag now resolves to Debian
# bookworm, which lacks libssl1.1 required by mongodb-org 4.4.
FROM python:3.8-bullseye

RUN rm /bin/sh && ln -s /bin/bash /bin/sh

# Bullseye is EOL and its packages have moved to archive.debian.org.
RUN echo "deb http://archive.debian.org/debian bullseye main" > /etc/apt/sources.list

# update + install in one layer so a cached, stale package index is never reused
RUN apt-get -y update && apt-get install -y curl nano wget nginx git

RUN curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add -
RUN echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list


# Mongo
RUN ln -s /bin/echo /bin/systemctl
RUN wget -qO - https://www.mongodb.org/static/pgp/server-4.4.asc | apt-key add -
RUN echo "deb http://repo.mongodb.org/apt/debian buster/mongodb-org/4.4 main" | tee /etc/apt/sources.list.d/mongodb-org-4.4.list
RUN apt-get -y update && apt-get install -y mongodb-org

# Install Yarn
RUN apt-get install -y yarn

# `easy_install pip` was removed: easy_install no longer exists in setuptools,
# and pip already ships with the python base image.


ENV ENV_TYPE staging
ENV MONGO_HOST mongo
ENV MONGO_PORT 27017
##########

ENV PYTHONPATH=$PYTHONPATH:/src/

# copy the dependencies file to the working directory
COPY src/requirements.txt .

# install dependencies
RUN pip install -r requirements.txt

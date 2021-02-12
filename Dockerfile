FROM ubuntu:18.04
ENV PYTHONUNBUFFERED 1

###### SETUP BASE INFRASTRUCTURE ######
RUN apt-get update && apt-get install -y python3.6 python3-pip curl build-essential vim libproj-dev proj-data proj-bin libgeos-dev libgdal-dev  redis-server daphne libboost-program-options1.65.1 libcliquer1 libgsl23 libgslcblas0 libtbb2
RUN curl -sL https://deb.nodesource.com/setup_10.x -o nodesource_setup.sh && bash nodesource_setup.sh && apt-get update && apt-get install -y nodejs && rm nodesource_setup.sh

RUN pip3 install -U pip

###### INSTALL PYTHON PACKAGES ######
ENV LC_CTYPE C.UTF-8
ENV LC_ALL C.UTF-8
ENV LANGUAGE C.UTF-8
ENV LANG C.UTF-8
RUN pip3 install cython numpy
COPY requirements.txt /
RUN pip3 install -Ur /requirements.txt
RUN pip3 uninstall --yes shapely
RUN pip3 uninstall --yes cartopy
RUN pip3 install shapely cartopy --no-binary shapely --no-binary cartopy

#COPY django-rest-authemail /django-rest-authemail
#RUN pip3 install -U -e /django-rest-authemail

###### SETUP APPLICATION INFRASTRUCTURE ######
COPY config /config
COPY wait-for-it.sh config/gunicorn.sh config/daphne.sh /
RUN chmod 755 /gunicorn.sh /wait-for-it.sh /daphne.sh


###### INSTALL JAVASCRIPT PACKAGES ######
COPY package*.json /
RUN npm install


###### INSTALL APPLICATION ######
COPY reactjs /reactjs
RUN cd / && npm run webpack
COPY src /src
COPY scip /scip
RUN apt install /scip/SCIPOptSuite-7.0.2-Linux-ubuntu.deb
WORKDIR /src

###### LABEL THE CURRENT IMAGE ######
ARG GIT_COMMIT_HASH
LABEL GIT_COMMIT_HASH=$GIT_COMMIT_HASH

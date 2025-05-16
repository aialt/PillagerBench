FROM python:3.10.13
COPY --from=openjdk:17-slim /usr/local/openjdk-17 /usr/local/openjdk-17

ENV JAVA_HOME /usr/local/openjdk-17

RUN update-alternatives --install /usr/bin/java java /usr/local/openjdk-17/bin/java 1

RUN apt update
RUN curl -sL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs

ADD ./requirements.txt ./requirements.txt

RUN pip install pip -U
RUN pip install -r requirements.txt

#RUN mkdir /PILLAGER/
#ADD . /PILLAGER/
#
#WORKDIR /PILLAGER/voyager/env/mineflayer
#RUN npm install
#WORKDIR mineflayer-collectblock
#RUN npx tsc
#WORKDIR /PILLAGER/voyager/env/mineflayer
#RUN npm install

WORKDIR /PILLAGER/

#EXPOSE 49172/tcp
#EXPOSE 49172/udp
#ENTRYPOINT python main.py
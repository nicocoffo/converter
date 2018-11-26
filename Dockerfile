FROM alpine

RUN apk --update add --no-cache py3-paramiko py3-crypto git mediainfo \
  && git clone https://github.com/nicocoffo/jackhammer.git /opt/jackhammer \
  && pip3 install py-crypto \
  && pip3 install --upgrade google-api-python-client \
  && pip3 install --upgrade pip \
  && pip3 install apache-libcloud \
  && pip3 install pyyaml \
  && pip3 install /opt/jackhammer \
  && pip3 install pymediainfo \
  && pip3 install plexapi \
  && rm -rf /var/cache/apk/* \
  && mkdir -p /opt/converter/scripts \
  && mkdir /state \
  && mkdir /data \
  && mkdir /config

EXPOSE 9234

COPY src/ /opt/replicant

WORKDIR /opt/replicant

CMD ["/usr/bin/python3", "replicant.py", "--config", "/config/config.yaml"]

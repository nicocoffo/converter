FROM alpine

RUN apk --update add --no-cache py3-paramiko git \
  && pip3 install --upgrade google-api-python-client \
  && git clone https://github.com/nicocoffo/jackhammer.git /opt/jackhammer \
  && pip3 install /opt/jackhammer \
  && rm -rf /var/cache/apk/* \
  && mkdir -p /opt/converter/scripts

EXPOSE 9321

COPY scripts/* /opt/converter/scripts/
COPY converter.py /opt/converter/converter.py

WORKDIR /opt/converter

CMD ["/usr/bin/python3", "converter.py"]

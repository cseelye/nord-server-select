FROM python:3.9
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade --requirement /tmp/requirements.txt && rm -f /tmp/requirements.txt
COPY server_select.py appdefaults.py /

WORKDIR /
ENTRYPOINT ["./server_select.py"]
CMD []

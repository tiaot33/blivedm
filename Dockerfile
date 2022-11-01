FROM python:3.8

WORKDIR /blivedm

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "./sample.py" ]
FROM python:2.7-alpine
ADD . /wxBot
WORKDIR /wxBot
RUN pip install requests
RUN pip install pyqrcode
RUN pip install pypng
RUN apk update && apk add zlib-dev && apk add jpeg-dev && apk add alpine-sdk
RUN pip install Pillow
CMD ["python", "bot.py"]


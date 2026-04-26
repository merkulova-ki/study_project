FROM python

WORKDIR /app

RUN pip install --upgrade pip

RUN mkdir -p static

COPY requirements.txt ./

RUN pip install -r requirements.txt

COPY src ./src

CMD uvicorn src.main:app --host 0.0.0.0 --port 8765 --reload


FROM python:3.10-slim

WORKDIR /app
ENV FLASK_APP=main
COPY requirements.txt requirements.txt
RUN pip3 install -r requrements.txt

COPY . .
EXPOSE 5000
CMD ["python3", "-m", "flask", "run"]

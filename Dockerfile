# Use the official Python image.
# https://hub.docker.com/_/python
FROM python:3.9

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . .

# Install production dependencies.
RUN pip install Flask gunicorn line-bot-sdk google-cloud-datastore python_dotenv nltk

# for install wget
RUN apt-get update && apt-get install -y wget

# for NLTK manual download
WORKDIR /usr/local/nltk_data/tokenizers
RUN wget "https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/tokenizers/punkt.zip" -O punkt.zip
RUN unzip punkt.zip

WORKDIR $APP_HOME
# Run the web service on container startup. Here we use the gunicorn
# webserver, with one worker process and 8 threads.
# For environments with multiple CPU cores, increase the number of workers
# to be equal to the cores available.
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 app:app
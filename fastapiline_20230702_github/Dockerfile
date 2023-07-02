# Use the official Python image as the base image
FROM python:3.9

# 以下の処理を行っていくときのuser
USER root

# Set the working directory
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

RUN apt-get update && apt-get install -y \
    libzbar0 \
    libgl1-mesa-glx

# Install the required packages
RUN pip install --no-cache-dir -r requirements.txt --default-timeout=100

# ローカル時はコメントアウト
EXPOSE 8080

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Copy the rest of the application code
COPY . .

# Start the application # ローカル時は8000, Google Cloud Run時は8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

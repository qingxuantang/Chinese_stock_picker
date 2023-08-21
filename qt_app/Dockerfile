
FROM python:3.9

# Set the working directory
WORKDIR /app

# Copy package.json and package-lock.json to the working directory
COPY requirements.txt ./requirements.txt

# Install dependencies
RUN pip install -r requirements.txt

# Expose the port the app will run on
EXPOSE 3000

COPY . /app

ENTRYPOINT [ "streamlit","run" ]

# Start the application
CMD ["main.py"]
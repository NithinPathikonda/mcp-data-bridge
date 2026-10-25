FROM python:3.12-slim

WORKDIR /app

# Copy dependency definition
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Initialize demo database
RUN python demo_db.py

EXPOSE 8500

# Default entrypoint: Run the interactive web playground
CMD ["python", "web_ui.py"]

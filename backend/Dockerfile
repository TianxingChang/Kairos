FROM agnohq/python:3.12

ARG USER=app
ARG APP_DIR=/app
ENV APP_DIR=${APP_DIR}

# Install system dependencies
RUN apt-get update && apt-get install -y \
  curl \
  && rm -rf /var/lib/apt/lists/*

# Create user and home directory
RUN groupadd -g 61000 ${USER} \
  && useradd -g 61000 -u 61000 -ms /bin/bash -d ${APP_DIR} ${USER}

WORKDIR ${APP_DIR}

# Copy requirements.txt
COPY requirements.txt ./

# Install requirements
RUN uv pip sync requirements.txt --system

# Verify requirements installation
RUN python -c "import youtube_transcript_api; print('youtube-transcript-api available')"

# Copy project files
COPY . .

# Set permissions for the /app directory
RUN chown -R ${USER}:${USER} ${APP_DIR}

# Switch to non-root user
USER ${USER}

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["chill"]

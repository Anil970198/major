FROM python:3.12-slim

WORKDIR /app

# System dependencies
RUN apt-get update && \
    apt-get install -y curl git build-essential && \
    curl https://sh.rustup.rs -sSf | sh -s -- -y && \
    ln -s /root/.cargo/bin/* /usr/local/bin/ && \
    rm -rf /var/lib/apt/lists/*

# Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Prevent venv creation
RUN poetry config virtualenvs.create false

# ✅ Copy everything first (code + pyproject)
COPY . .

# ✅ Install all dependencies (with code present)
RUN poetry install --no-interaction --no-ansi --with dev

# Run the app
CMD ["poetry", "run", "python", "app.py"]

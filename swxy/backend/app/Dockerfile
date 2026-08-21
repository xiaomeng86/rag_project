FROM python:3.11.10-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt requirements-test.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --prefix=/install -r requirements.txt
COPY scripts/download_nltk_data.py ./download_nltk_data.py
RUN mkdir -p /nltk_data \
    && PYTHONPATH=/install/lib/python3.11/site-packages \
       NLTK_DATA=/nltk_data python ./download_nltk_data.py


FROM python:3.11.10-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NLTK_DATA=/usr/local/share/nltk_data \
    UPLOAD_DIR=/data/uploads

RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY --from=builder /nltk_data /usr/local/share/nltk_data
WORKDIR /app
COPY . /app
RUN chmod +x /app/start.sh \
    && mkdir -p /data/uploads

EXPOSE 8000
ENTRYPOINT ["/app/start.sh"]
CMD ["uvicorn", "app_main:app", "--host", "0.0.0.0", "--port", "8000"]


FROM runtime AS test

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install -r /app/requirements-test.txt
ENTRYPOINT []
CMD ["pytest", "-q"]


FROM runtime AS final

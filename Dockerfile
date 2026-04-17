FROM python:3.12-slim
LABEL org.opencontainers.image.authors="Greenshift <contact@greenshift.app>"
COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /usr/local/bin/uv

WORKDIR /usr/src/app

ENV PYTHONPATH="/usr/src/app"
ENV VIRTUAL_ENV="/usr/src/app/.venv"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY pyproject.toml uv.lock ./
COPY kube_service_selectors ./kube_service_selectors/
RUN uv sync --frozen --no-dev --no-cache

ENTRYPOINT ["/usr/src/app/kube_service_selectors/main.py"]

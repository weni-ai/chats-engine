# syntax = docker/dockerfile:1

ARG PYTHON_VERSION="3.8"
ARG DEBIAN_VERSION="buster"
ARG POETRY_VERSION="1.1.15"
ARG REQUESTS_VERSION="2.29.0"

ARG BUILD_DEPS="\
    python3-dev \
    build-essential \
    gettext \
    libpq-dev \
    cmake \
    pkg-config \
    autoconf \
    libtool \
    automake"

ARG RUNTIME_DEPS="\
    tzdata \
    curl \
    gosu \
    gettext \
    postgresql-client \
    ffmpeg \
    libmagic1"

FROM python:${PYTHON_VERSION}-slim-${DEBIAN_VERSION} AS base

ARG APP_PORT="8000"

ARG APP_VERSION="0.1"

ENV APPLICATION_NAME="Chats"  \
    APP_VERSION=${APP_VERSION} \
    RUNTIME_DEPS=${RUNTIME_DEPS} \
    PROJECT_PATH="/chats"  \
    BUILD_DEPS=${BUILD_DEPS} \
    APP_UID=${APP_UID} \
    APP_GID=${APP_GID} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/install/bin:${PATH}" \
    APP_PORT=${APP_PORT}

LABEL app=${VERSION} \
    os="debian" \
    os.version="12" \
    name="${APPLICATION_NAME} ${APP_VERSION}" \
    description="${APPLICATION_NAME} image" \
    maintainer="${APPLICATION_NAME} Team" \
    org.opencontainers.image.url="https://github.com/weni-ai/chats-engine" \
    org.opencontainers.image.documentation="https://github.com/weni-ai/chats-engine" \
    org.opencontainers.image.source="https://github.com/weni-ai/chats-engine" \
    org.opencontainers.image.title="Chats"

ARG APP_UID=1000
ARG APP_GID=1000

RUN addgroup --gid "${APP_GID}" app_group \
    && useradd --system -m -d ${PROJECT_PATH} -u "${APP_UID}" -g "${APP_GID}" app_user

# set work directory
WORKDIR ${PROJECT_PATH}

RUN rm -f /etc/apt/apt.conf.d/docker-clean; echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache

# RUN if [ ! "x${BUILD_DEPS}" = "x" ] ; then apt-get update \
#     && apt-get install -y --no-install-recommends ${BUILD_DEPS} ; fi

FROM base AS build-poetry

ARG POETRY_VERSION
ARG REQUESTS_VERSION
ARG NODE_VERSION

COPY ./pyproject.toml .
COPY ./poetry.lock .

RUN --mount=type=cache,mode=0755,target=/pip_cache,id=pip pip install --cache-dir /pip_cache -U poetry=="${POETRY_VERSION}" \
  && poetry cache clear -n --all pypi \
  && pip install --cache-dir /pip_cache requests=="${REQUESTS_VERSION}" \
  && poetry export --without-hashes --output requirements.txt
#  && poetry add -n --lock $(cat pip-requires.txt) \

FROM build as build-pip

ARG BUILD_DEPS

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
  --mount=type=cache,target=/var/lib/apt,sharing=locked \
  apt-get update \
  && apt-get install --no-install-recommends --no-install-suggests -y ${BUILD_DEPS}

COPY --from=build-poetry /requirements.txt .

RUN --mount=type=cache,mode=0755,target=/pip_cache,id=pip pip install --cache-dir /pip_cache --prefix=/install -r /tmp/dep/requirements.txt

# RUN mkdir /install \
#     && pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM base

ARG BUILD_DEPS
ARG RUNTIME_DEPS

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
  --mount=type=cache,target=/var/lib/apt,sharing=locked \
  apt-get update \
  && SUDO_FORCE_REMOVE=yes apt-get remove --purge -y ${BUILD_DEPS} \
  && apt-get autoremove -y \
  && apt-get install -y --no-install-recommends ${RUNTIME_DEPS} \
  && rm -rf /usr/share/man /usr/share/doc

# COPY --chown=${PROJECT_USER}:${PROJECT_GROUP} package.json package-lock.json ${PROJECT_PATH}

COPY --from=build-pip /install /usr/local

# # Clear image and install runtime dependences
# RUN apt-get update \
#     && SUDO_FORCE_REMOVE=yes apt-get remove --purge -y ${BUILD_DEPS} \
#     && apt-get autoremove -y \
#     && apt-get install -y --no-install-recommends ${RUNTIME_DEPS} \
#     && rm -rf /usr/share/man \
#     && apt-get clean \
#     && rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,id=npm,target=/npm_cache \
  npm install --global --ignore-scripts --cache /npm_cache \
  coffeescript \
  less \
  yarn \
  && npm install --ignore-scripts --cache /npm_cache

COPY --from=build /install /usr/local
COPY --chown=${PROJECT_USER}:${PROJECT_GROUP} . ${PROJECT_PATH}

USER "${PROJECT_USER}:${PROJECT_USER}"
RUN chmod 777 docker-entrypoint.sh

CMD ["sh", "docker-entrypoint.sh"]
#ENTRYPOINT ["docker-entrypoint.sh"]

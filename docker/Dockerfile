# syntax = docker/dockerfile:1

ARG PYTHON_VERSION="3.8"
ARG DEBIAN_VERSION="buster"
ARG POETRY_VERSION="1.1.15"
ARG REQUESTS_VERSION="2.29.0"

ARG APP_UID=1999
ARG APP_GID=1999

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

FROM python:${PYTHON_VERSION}-slim-${DEBIAN_VERSION} as base

ARG POETRY_VERSION
ARG REQUESTS_VERSION

ARG APP_PORT="8000"
ARG APP_VERSION="0.1"

# set environment variables
ENV APP_VERSION=${APP_VERSION} \
    RUNTIME_DEPS=${RUNTIME_DEPS} \
    BUILD_DEPS=${BUILD_DEPS} \
    APPLICATION_NAME="Chats" \
    PROJECT_PATH=/chats \
    PROJECT_USER=app_user \
    PROJECT_GROUP=app_group \
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
    os.version="10" \
    name="${APPLICATION_NAME} ${APP_VERSION}" \
    description="${APPLICATION_NAME} image" \
    maintainer="${APPLICATION_NAME} Team"

RUN addgroup --gid "${APP_GID}" "${PROJECT_GROUP}" \
    && useradd --system -m -d ${PROJECT_PATH} -u "${APP_UID}" -g "${APP_GID}" "${PROJECT_USER}"

# set work directory
WORKDIR ${PROJECT_PATH}

RUN rm -f /etc/apt/apt.conf.d/docker-clean; echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache

# FROM base AS build

# RUN if [ ! "x${BUILD_DEPS}" = "x" ] ; then apt-get update \
#     && apt-get install -y --no-install-recommends ${BUILD_DEPS} ; fi

FROM build as build-poetry

ARG POETRY_VERSION
ARG REQUESTS_VERSION

COPY ./pyproject.toml .
COPY ./poetry.lock .

# RUN python -m pip install -U poetry \
#     && poetry export --without-hashes --output /requirements.txt

RUN --mount=type=cache,mode=0755,target=/pip_cache,id=pip pip install --cache-dir /pip_cache -U poetry=="${POETRY_VERSION}" \
  && poetry cache clear -n --all pypi \
  && pip install --cache-dir /pip_cache requests=="${REQUESTS_VERSION}" \
  && poetry export --without-hashes --output requirements.txt

# FROM build as build-pip

# COPY --from=build-poetry /requirements.txt .

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
  && rm -rf /usr/share/man /usr/share/doc \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

COPY --chown=${PROJECT_USER}:${PROJECT_GROUP} package.json package-lock.json ${PROJECT_PATH}

COPY --from=build-pip /install /usr/local

# Clear image and install runtime dependences
# RUN apt-get update \
#     && SUDO_FORCE_REMOVE=yes apt-get remove --purge -y ${BUILD_DEPS} \
#     && apt-get autoremove -y \
#     && apt-get install -y --no-install-recommends ${RUNTIME_DEPS} \
#     && rm -rf /usr/share/man \
#     && apt-get clean \
#     && rm -rf /var/lib/apt/lists/*

# copy project
COPY --chown=${PROJECT_USER}:${PROJECT_GROUP} . ${PROJECT_PATH}

USER "${PROJECT_USER}:${PROJECT_USER}"
RUN chmod 777 docker-entrypoint.sh

CMD ["sh", "docker-entrypoint.sh"]
#ENTRYPOINT ["docker-entrypoint.sh"]

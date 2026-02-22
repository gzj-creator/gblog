ARG STATIC_BASE_IMAGE=ubuntu-24.04:galay-web-1.0
ARG GALAY_KERNEL_BACKEND=epoll

FROM ${STATIC_BASE_IMAGE} AS builder
ARG GALAY_KERNEL_BACKEND

WORKDIR /src/service/backend
COPY CMakeLists.txt /src/service/backend/CMakeLists.txt
COPY BlogServer.cc /src/service/backend/BlogServer.cc

RUN set -eu; \
    KERNEL_BACKEND="${GALAY_KERNEL_BACKEND:-epoll}"; \
    if ! command -v cmake >/dev/null 2>&1; then \
      echo "[error] cmake not found in base image"; exit 1; \
    fi; \
    BUILD_DIR=/tmp/backend-build; \
    if command -v ninja >/dev/null 2>&1; then \
      cmake -S /src/service/backend -B "${BUILD_DIR}" -G Ninja \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_PREFIX_PATH=/usr/local \
        -DGALAY_KERNEL_BACKEND="${KERNEL_BACKEND}"; \
    else \
      cmake -S /src/service/backend -B "${BUILD_DIR}" \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_PREFIX_PATH=/usr/local \
        -DGALAY_KERNEL_BACKEND="${KERNEL_BACKEND}"; \
    fi; \
    cmake --build "${BUILD_DIR}" --parallel; \
    cp "${BUILD_DIR}/bin/backend-server" /tmp/backend-server

FROM scratch AS artifact
COPY --from=builder /tmp/backend-server /backend-server

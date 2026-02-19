ARG STATIC_BASE_IMAGE=ubuntu-24.04:galay-web-1.0
ARG GALAY_KERNEL_BACKEND=epoll

FROM ${STATIC_BASE_IMAGE} AS builder

WORKDIR /src/service/static
COPY CMakeLists.txt /src/service/static/CMakeLists.txt
COPY src/main.cc /src/service/static/src/main.cc
COPY src/StaticServerConfig.h /src/service/static/src/StaticServerConfig.h
COPY src/StaticServerConfig.cc /src/service/static/src/StaticServerConfig.cc

RUN set -eu; \
    if ! command -v cmake >/dev/null 2>&1; then \
      echo "[error] cmake not found in base image"; exit 1; \
    fi; \
    BUILD_DIR=/tmp/static-build; \
    if command -v ninja >/dev/null 2>&1; then \
      cmake -S /src/service/static -B "${BUILD_DIR}" -G Ninja \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_PREFIX_PATH=/usr/local \
        -DGALAY_KERNEL_BACKEND="${GALAY_KERNEL_BACKEND}"; \
    else \
      cmake -S /src/service/static -B "${BUILD_DIR}" \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_PREFIX_PATH=/usr/local \
        -DGALAY_KERNEL_BACKEND="${GALAY_KERNEL_BACKEND}"; \
    fi; \
    cmake --build "${BUILD_DIR}" -j"$(nproc)"; \
    cp "${BUILD_DIR}/static-server" /tmp/static-server

FROM scratch AS artifact
COPY --from=builder /tmp/static-server /static-server

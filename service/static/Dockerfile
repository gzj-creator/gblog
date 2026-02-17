# syntax=docker/dockerfile:1.7

FROM ubuntu:24.04 AS builder
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    ninja-build \
    pkg-config \
    ca-certificates \
    libssl-dev \
    libspdlog-dev \
    && rm -rf /var/lib/apt/lists/*

ARG GALAY_KERNEL_REPO=https://github.com/gzj-creator/galay-kernel.git
ARG GALAY_KERNEL_REF=main
ARG GALAY_HTTP_REPO=https://github.com/gzj-creator/galay-http.git
ARG GALAY_HTTP_REF=main

WORKDIR /tmp/deps

RUN git clone --depth 1 --branch "${GALAY_KERNEL_REF}" "${GALAY_KERNEL_REPO}" galay-kernel \
    && cmake -S galay-kernel -B galay-kernel/build -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_TESTS=OFF \
    -DBUILD_BENCHMARKS=OFF \
    -DBUILD_EXAMPLES=OFF \
    -DCMAKE_INSTALL_PREFIX=/usr/local \
    && cmake --build galay-kernel/build -j"$(nproc)" \
    && cmake --install galay-kernel/build

RUN git clone --depth 1 --branch "${GALAY_HTTP_REF}" "${GALAY_HTTP_REPO}" galay-http \
    && cmake -S galay-http -B galay-http/build -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_TESTS=OFF \
    -DBUILD_BENCHMARKS=OFF \
    -DBUILD_EXAMPLES=OFF \
    -DBUILD_MODULE_EXAMPLES=OFF \
    -DCMAKE_PREFIX_PATH=/usr/local \
    -DCMAKE_INSTALL_PREFIX=/usr/local \
    && cmake --build galay-http/build -j"$(nproc)" \
    && cmake --install galay-http/build

WORKDIR /src
COPY service/static/main.cc /src/service/static/main.cc
COPY service/static/compiler.sh /src/service/static/compiler.sh

RUN chmod +x /src/service/static/compiler.sh \
    && GALAY_HTTP_DIR=/usr/local/include \
    GALAY_KERNEL_DIR=/usr/local/include \
    GALAY_HTTP_LIB_DIR=/usr/local/lib \
    GALAY_KERNEL_LIB_DIR=/usr/local/lib \
    /src/service/static/compiler.sh \
    && mv /src/service/static/server /tmp/static-server

FROM ubuntu:24.04 AS runtime
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libssl3 \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /usr/local/lib/libgalay-kernel.so* /usr/local/lib/
COPY --from=builder /usr/local/lib/libgalay-http.so* /usr/local/lib/
COPY --from=builder /tmp/static-server /app/static-server
COPY frontend/ /app/frontend/

ENV STATIC_HOST=0.0.0.0
ENV STATIC_PORT=8080
ENV STATIC_FRONTEND_ROOT=/app/frontend
ENV API_PROXY_UPSTREAM_HOST=127.0.0.1
ENV API_PROXY_UPSTREAM_PORT=8081
ENV LD_LIBRARY_PATH=/usr/local/lib:${LD_LIBRARY_PATH}

EXPOSE 8080
CMD ["/app/static-server"]

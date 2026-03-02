ARG GALAY_BASE_IMAGE=ubuntu:galay-v1
ARG GALAY_KERNEL_BACKEND=epoll

FROM ${GALAY_BASE_IMAGE} AS builder
ARG GALAY_KERNEL_BACKEND

WORKDIR /src/service/gateway
COPY . .

RUN set -eu; \
    KERNEL_BACKEND="${GALAY_KERNEL_BACKEND:-epoll}"; \
    BUILD_DIR=/tmp/gateway-build; \
    if command -v ninja >/dev/null 2>&1; then \
      cmake -S . -B "${BUILD_DIR}" -G Ninja \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_PREFIX_PATH=/usr/local \
        -DGALAY_KERNEL_BACKEND="${KERNEL_BACKEND}"; \
    else \
      cmake -S . -B "${BUILD_DIR}" \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_PREFIX_PATH=/usr/local \
        -DGALAY_KERNEL_BACKEND="${KERNEL_BACKEND}"; \
    fi; \
    cmake --build "${BUILD_DIR}" --parallel; \
    cp "${BUILD_DIR}/static-server" /tmp/static-server

FROM ${GALAY_BASE_IMAGE} AS runtime

WORKDIR /app
RUN mkdir -p /app/bin /app/config /app/logs /app/frontend

COPY --from=builder /tmp/static-server /app/bin/static-server
COPY config/static-server.conf /app/config/static-server.conf

ENV LD_LIBRARY_PATH=/usr/local/lib

EXPOSE 80

CMD ["./bin/static-server"]

FROM scratch AS artifact
COPY --from=builder /tmp/static-server /static-server

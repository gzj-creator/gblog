ARG GALAY_BASE_IMAGE=ubuntu:galay-v1
ARG GALAY_KERNEL_BACKEND=epoll

FROM ${GALAY_BASE_IMAGE} AS builder
ARG GALAY_KERNEL_BACKEND

WORKDIR /src/service/db
COPY . .

RUN set -eu; \
    KERNEL_BACKEND="${GALAY_KERNEL_BACKEND:-epoll}"; \
    BUILD_DIR=/tmp/db-build; \
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
    cp "${BUILD_DIR}/bin/db-server" /tmp/db-server

FROM ${GALAY_BASE_IMAGE} AS runtime

WORKDIR /app
RUN mkdir -p /app/bin /app/config /app/logs

COPY --from=builder /tmp/db-server /app/bin/db-server

ENV LD_LIBRARY_PATH=/usr/local/lib

EXPOSE 8082

CMD ["./bin/db-server", "-h", "0.0.0.0", "-p", "8082"]

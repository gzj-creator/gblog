# Blog Service Dockerfile
# 基于 Ubuntu 24.04

FROM ubuntu:24.04 AS builder

# 避免交互式安装
ENV DEBIAN_FRONTEND=noninteractive

# 安装构建依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制 galay 库（假设已预编译）
# 实际部署时需要先构建 galay-kernel 和 galay-http
COPY --from=galay-libs /usr/local/lib/libgalay-kernel.so /usr/local/lib/
COPY --from=galay-libs /usr/local/lib/libgalay-http.so /usr/local/lib/
COPY --from=galay-libs /usr/local/include/galay-kernel /usr/local/include/galay-kernel
COPY --from=galay-libs /usr/local/include/galay-http /usr/local/include/galay-http

# 设置工作目录
WORKDIR /app

# 复制源代码
COPY . .

# 构建
RUN mkdir -p build && cd build && \
    cmake -DCMAKE_BUILD_TYPE=Release .. && \
    make -j$(nproc)

# ============================================
# 运行时镜像
# ============================================
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    libssl3 \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN useradd -m -s /bin/bash appuser

# 复制 galay 库
COPY --from=builder /usr/local/lib/libgalay-kernel.so /usr/local/lib/
COPY --from=builder /usr/local/lib/libgalay-http.so /usr/local/lib/

# 更新动态链接库缓存
RUN ldconfig

# 复制可执行文件
COPY --from=builder /app/build/bin/blog-server /usr/local/bin/

WORKDIR /app

# 设置权限
RUN chown -R appuser:appuser /app

# 切换到非 root 用户
USER appuser

# 暴露端口
EXPOSE 8080

# 环境变量
ENV BLOG_HOST=0.0.0.0
ENV BLOG_PORT=8080
# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# 启动服务
CMD ["blog-server", "-h", "0.0.0.0", "-p", "8080"]

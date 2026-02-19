#!/bin/bash
# S1-RunServer.sh
# 运行博客服务器

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/build"

# 默认参数
HOST="0.0.0.0"
PORT=8080
STATIC_DIR="$PROJECT_DIR/../../frontend"

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--host)
            HOST="$2"
            shift 2
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -s|--static)
            STATIC_DIR="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  -h, --host <host>    Server host (default: 0.0.0.0)"
            echo "  -p, --port <port>    Server port (default: 8080)"
            echo "  -s, --static <dir>   Static files directory"
            echo "  --help               Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# 检查构建目录
if [ ! -d "$BUILD_DIR" ]; then
    echo "[INFO] Build directory not found, building..."
    mkdir -p "$BUILD_DIR"
    cd "$BUILD_DIR"
    cmake .. -DCMAKE_BUILD_TYPE=Release
    make -j$(nproc 2>/dev/null || sysctl -n hw.ncpu)
fi

# 检查可执行文件
SERVER_BIN="$BUILD_DIR/bin/backend-server"
if [ ! -f "$SERVER_BIN" ]; then
    echo "[ERROR] Server binary not found: $SERVER_BIN"
    echo "[INFO] Please build the project first"
    exit 1
fi

# 检查静态文件目录
if [ ! -d "$STATIC_DIR" ]; then
    echo "[ERROR] Static directory not found: $STATIC_DIR"
    exit 1
fi

echo "============================================"
echo "Starting Galay Blog Server"
echo "============================================"
echo "Host: $HOST"
echo "Port: $PORT"
echo "Static: $STATIC_DIR"
echo "============================================"

# 运行服务器
exec "$SERVER_BIN" -h "$HOST" -p "$PORT" -s "$STATIC_DIR"

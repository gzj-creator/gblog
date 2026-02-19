#!/bin/bash
# S2-RunTests.sh
# 运行测试用例

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/build"

echo "============================================"
echo "Galay Blog Server - Test Runner"
echo "============================================"

# 检查构建目录
if [ ! -d "$BUILD_DIR" ]; then
    echo "[INFO] Build directory not found, building..."
    mkdir -p "$BUILD_DIR"
    cd "$BUILD_DIR"
    cmake .. -DCMAKE_BUILD_TYPE=Debug -DBUILD_TESTS=ON
    make -j$(nproc 2>/dev/null || sysctl -n hw.ncpu)
fi

cd "$BUILD_DIR"

# 启动服务器（后台运行）
SERVER_BIN="$BUILD_DIR/bin/backend-server"
STATIC_DIR="$PROJECT_DIR/../../frontend"

if [ ! -f "$SERVER_BIN" ]; then
    echo "[ERROR] Server binary not found"
    exit 1
fi

echo "[INFO] Starting server in background..."
"$SERVER_BIN" -p 8080 -s "$STATIC_DIR" &
SERVER_PID=$!

# 等待服务器启动
sleep 2

# 检查服务器是否运行
if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "[ERROR] Server failed to start"
    exit 1
fi

echo "[INFO] Server started with PID: $SERVER_PID"

# 运行测试
echo "[INFO] Running API tests..."
TEST_PASSED=0
TEST_FAILED=0

# 运行测试程序
for TEST_BIN in "$BUILD_DIR/bin/T"*; do
    if [ -x "$TEST_BIN" ]; then
        TEST_NAME=$(basename "$TEST_BIN")
        echo "[INFO] Running $TEST_NAME..."
        "$TEST_BIN"
        if [ $? -eq 0 ]; then
            ((TEST_PASSED++))
        else
            ((TEST_FAILED++))
        fi
    fi
done

# 停止服务器
echo "[INFO] Stopping server..."
kill $SERVER_PID 2>/dev/null
wait $SERVER_PID 2>/dev/null

# 输出结果
echo "============================================"
echo "Test Results"
echo "============================================"
echo "Passed: $TEST_PASSED"
echo "Failed: $TEST_FAILED"
echo "============================================"

if [ $TEST_FAILED -gt 0 ]; then
    exit 1
fi

exit 0

#!/bin/bash
# S3-Build.sh
# 构建项目

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/build"

# 默认构建类型
BUILD_TYPE="Release"
BUILD_TESTS="ON"

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --debug)
            BUILD_TYPE="Debug"
            shift
            ;;
        --release)
            BUILD_TYPE="Release"
            shift
            ;;
        --no-tests)
            BUILD_TESTS="OFF"
            shift
            ;;
        --clean)
            echo "[INFO] Cleaning build directory..."
            rm -rf "$BUILD_DIR"
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --debug      Build in debug mode"
            echo "  --release    Build in release mode (default)"
            echo "  --no-tests   Don't build tests"
            echo "  --clean      Clean build directory first"
            echo "  --help       Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "============================================"
echo "Galay Blog Server - Build"
echo "============================================"
echo "Build Type: $BUILD_TYPE"
echo "Build Tests: $BUILD_TESTS"
echo "============================================"

# 创建构建目录
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# 配置
echo "[INFO] Configuring CMake..."
cmake .. \
    -DCMAKE_BUILD_TYPE="$BUILD_TYPE" \
    -DBUILD_TESTS="$BUILD_TESTS"

if [ $? -ne 0 ]; then
    echo "[ERROR] CMake configuration failed"
    exit 1
fi

# 编译
echo "[INFO] Building..."
make -j$(nproc 2>/dev/null || sysctl -n hw.ncpu)

if [ $? -ne 0 ]; then
    echo "[ERROR] Build failed"
    exit 1
fi

echo "============================================"
echo "Build completed successfully!"
echo "============================================"
echo "Binary: $BUILD_DIR/bin/blog-server"
echo "============================================"

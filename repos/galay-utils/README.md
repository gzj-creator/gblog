# galay-utils

[![C++20](https://img.shields.io/badge/C%2B%2B-20-blue.svg)](https://en.cppreference.com/w/cpp/20)
[![CMake](https://img.shields.io/badge/CMake-3.16+-green.svg)](https://cmake.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

一个现代化的C++20工具库，提供常用功能的高性能实现。

## 特性

- **现代化C++**: 使用C++20特性，提供类型安全和性能优化
- **跨平台**: 支持Linux、macOS和Windows
- **无依赖**: 纯头文件库，无外部依赖
- **高性能**: 针对性能优化，提供高效实现
- **易使用**: 简洁的API设计，完善的文档

## 模块

### 核心工具
- **String**: 字符串处理工具（分割、连接、修剪、转换等）
- **Random**: 高质量随机数生成器
- **System**: 系统级功能（文件、时间、环境变量等）

### 数据结构
- **TrieTree**: 前缀树实现
- **ConsistentHash**: 一致性哈希算法
- **Mvcc**: 多版本并发控制

### 并发编程
- **Thread**: 线程池和线程安全容器
- **Pool**: 对象池和阻塞对象池

### 网络与分布式
- **RateLimiter**: 多算法速率限制器
- **CircuitBreaker**: 熔断器模式实现
- **Balancer**: 多种负载均衡算法

### 编码与压缩
- **Huffman**: 霍夫曼编码算法

### 应用框架
- **App**: 命令行参数解析
- **Parser**: 配置文件解析（INI、环境变量）

### 系统集成
- **Process**: 进程管理
- **SignalHandler**: 信号处理
- **BackTrace**: 栈追踪

## 快速开始

### 环境准备（macOS / Linux）

```bash
# macOS (Homebrew)
brew install cmake

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y cmake g++
```

### 使用CMake构建

```bash
# 克隆仓库
git clone https://github.com/gzj-creator/galay-utils.git
cd galay-utils

# 创建构建目录
mkdir build && cd build

# 配置和构建
cmake ..
cmake --build . --parallel

# 运行测试
ctest --output-on-failure
```

### 集成到您的项目

#### 方法1: 作为子模块

```bash
git submodule add https://github.com/gzj-creator/galay-utils.git third_party/galay-utils
```

在CMakeLists.txt中添加：

```cmake
add_subdirectory(third_party/galay-utils)
target_link_libraries(your_target galay-utils)
```

#### 方法2: 安装库

```bash
cd galay-utils
mkdir build && cd build
cmake ..
cmake --build . --parallel
sudo cmake --install .
```

然后在您的项目中使用：

```cmake
find_package(galay-utils REQUIRED)
target_link_libraries(your_target galay::galay-utils)
```

#### 方法3: Bazel安装

```bash
# 构建头文件包
bazel build //:headers

# 手动复制头文件到系统目录
sudo cp -r bazel-bin/headers/** /usr/local/include/galay-utils/
```

然后在BUILD.bazel中使用：

```python
cc_library(
    name = "my_library",
    hdrs = ["my_header.h"],
    deps = ["@galay_utils//:galay-utils"],
)
```

### 基本使用

```cpp
#include <galay-utils/galay-utils.hpp>
#include <iostream>

using namespace galay::utils;

int main() {
    // 字符串处理
    auto parts = StringUtils::split("hello,world", ',');
    std::cout << StringUtils::join(parts, " ") << std::endl;

    // 随机数生成
    auto& rng = Randomizer::instance();
    int random_num = rng.randomInt(1, 100);

    // 系统信息
    std::cout << "CPU cores: " << System::cpuCount() << std::endl;
    std::cout << "Hostname: " << System::hostname() << std::endl;

    return 0;
}
```

## 构建要求

- **C++编译器**: 支持C++20 (GCC 10+, Clang 10+, MSVC 2019 16.8+)
- **构建工具**: CMake 3.16+
- **操作系统**: Linux, macOS, Windows

## 构建选项

| 选项 | 默认值 | 描述 |
|------|--------|------|
| `BUILD_TESTS` | `OFF` | 构建测试套件 |

## C++23 模块支持更新（2026-02）

本次已将模块接口统一为现代 C++ 范式：

- `module;`
- `#include "galay-utils/module/ModulePrelude.hpp"`
- `export module galay.utils;`
- `export { #include ... }`

模块接口文件：`galay-utils/module/galay.utils.cppm`  
预导入头文件：`galay-utils/module/ModulePrelude.hpp`

推荐构建条件：

- CMake `>= 3.28`
- `Ninja` 或 `Visual Studio` 生成器
- Clang 工具链需可用 `clang-scan-deps`

示例（Clang 20）：

```bash
cmake -S . -B build-mod -G Ninja \
  -DCMAKE_CXX_COMPILER=/opt/homebrew/opt/llvm@20/bin/clang++
cmake --build build-mod --target galay-utils-modules --parallel
```

```bash
# 构建测试
cmake -DBUILD_TESTS=ON ..
cmake --build . --parallel
ctest --output-on-failure
```

## 文档

详细文档请查看 [docs/](docs/) 目录：

- [String 模块](docs/string.md)
- [Random 模块](docs/random.md)
- [System 模块](docs/system.md)
- [Thread 模块](docs/thread.md)
- [Pool 模块](docs/pool.md)
- [RateLimiter 模块](docs/ratelimiter.md)
- [CircuitBreaker 模块](docs/circuitbreaker.md)
- [ConsistentHash 模块](docs/consistent_hash.md)
- [Balancer 模块](docs/balancer.md)
- [Trie 模块](docs/trie.md)
- [MVCC 模块](docs/mvcc.md)
- [Parser 模块](docs/parser.md)
- [App 模块](docs/app.md)
- [Process 模块](docs/process.md)
- [Signal 模块](docs/signal.md)
- [BackTrace 模块](docs/backtrace.md)
- [Huffman 模块](docs/huffman.md)
- [TypeName 模块](docs/typename.md)

## 许可证

本项目采用 MIT 许可证。

## 贡献

欢迎提交Issue和Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 作者

- galay-utils contributors

## 性能优化特性

### 🚀 高性能设计

- **零拷贝文件读取**: 使用预分配内存避免不必要的拷贝操作
- **智能锁竞争**: 参数验证在加锁前进行，减少锁竞争
- **内存预分配**: 字符串生成使用预分配策略提升性能
- **边界检查优化**: 提前返回无效参数，避免不必要的计算

### 📊 优化亮点

- **随机数生成器**: 参数检查前置，避免无效参数的锁竞争
- **字符串处理**: 修复边界情况，优化分割算法
- **文件操作**: 使用`std::ios::ate`实现高效的文件大小获取和读取

## 致谢

- 感谢所有贡献者
- 感谢开源社区提供的技术支持

# galay-utils 使用文档

> Generated from `/Users/gongzhijie/Desktop/projects/git/gblob/service/blog/frontend/docs/galay-utils.html` for AI vector indexing.

## 概览

galay-utils 是 Galay 库体系的基础工具库，提供字符串、并发、限流、负载均衡等通用能力。

它以头文件为主并强调可组合性，复杂业务框架与领域逻辑需在上层实现。

## 架构

- **Header-only 设计** — 主体以头文件发布，按需引入，不强制运行时组件
- **基础能力分层** — 字符串/随机/系统工具、并发原语、分布式辅助、编码组件
- **模块化导出** — 支持 `galay.utils` C++23 命名模块（工具链满足时）

### 模块矩阵

模块头文件说明

StringUtilsstring/String.hpp字符串分割、拼接、trim、大小写转换
Randomrandom/Random.hpp随机数与随机字符串能力
Systemsystem/System.hpp系统信息、文件与环境能力
ThreadPoolthread/Thread.hpp固定大小线程池与任务提交
TokenBucketLimiterratelimiter/RateLimiter.hpp令牌桶/滑窗/漏桶限流实现
CircuitBreakercircuitbreaker/CircuitBreaker.hpp熔断器，支持半开恢复
LoadBalancerbalancer/LoadBalancer.hpp轮询、加权轮询、随机、加权随机
ConsistentHashconsistent_hash/ConsistentHash.hpp一致性哈希路由

## 核心 API

### StringUtils

```cpp
#include

using namespace galay::utils;

// 分割与拼接
auto parts = StringUtils::split("hello,world,cpp", ',');
// parts: {"hello", "world", "cpp"}
auto joined = StringUtils::join(parts, " | ");
// joined: "hello | world | cpp"

// Trim
auto trimmed = StringUtils::trim("  hello  ");
// trimmed: "hello"

// 大小写
auto upper = StringUtils::toUpper("hello");  // "HELLO"
auto lower = StringUtils::toLower("HELLO");  // "hello"

// 前缀/后缀判断
bool starts = StringUtils::startsWith("hello.cpp", "hello");  // true
bool ends = StringUtils::endsWith("hello.cpp", ".cpp");        // true

// 替换
auto replaced = StringUtils::replace("foo bar foo", "foo", "baz");
// replaced: "baz bar baz"
```

### ThreadPool

```cpp
#include

ThreadPool pool(4);  // 4 个工作线程

// 提交任务，获取 future
auto future = pool.submit([]() {
    // 耗时计算...
    return 42;
});

int result = future.get();  // 阻塞等待结果

// 批量提交
std::vector> futures;
for (int i = 0; i

// 每秒 100 个令牌，桶容量 200（允许突发）
TokenBucketLimiter limiter(100, 200);

if (limiter.tryAcquire()) {
    // 允许请求
    handleRequest();
} else {
    // 限流，返回 429
    return tooManyRequests();
}

// 协程等待令牌（支持 timeout）
Coroutine throttle() {
    auto result = co_await limiter.acquire(1).timeout(std::chrono::milliseconds(100));
    co_return;
}
```

### CircuitBreaker（熔断器）

```cpp
#include

CircuitBreakerConfig config;
config.failureThreshold = 5;
config.successThreshold = 3;
config.resetTimeout = std::chrono::seconds(30);

CircuitBreaker breaker(config);

auto result = breaker.execute([&]() {
    return callRemoteService();
});

if (!result) {
    if (breaker.state() == CircuitState::Open) {
        // 熔断中，走降级逻辑
        return fallback();
    }
}
```

### LoadBalancer

```cpp
#include

// 轮询
RoundRobinLoadBalancer rr({
    "192.168.1.1:8080",
    "192.168.1.2:8080"
});
auto node = rr.select();

// 加权轮询
WeightRoundRobinLoadBalancer wrr(
    {"node1", "node2"}, {3, 1});
auto weighted = wrr.select();
```

### 示例入口

- 示例代码可参考仓库 README 的“基本使用”片段
- 各模块文档位于 `docs/*.md`（如 `docs/string.md`、`docs/thread.md`）

## 安装与构建

### macOS

```bash
brew install cmake ninja pkg-config
# 根据下方“依赖”章节补充库（如 openssl、spdlog、simdjson、liburing 等）
```

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y build-essential cmake ninja-build pkg-config
# 根据下方“依赖”章节补充库（如 libssl-dev、libspdlog-dev、libsimdjson-dev、liburing-dev 等）
```

### 通用构建

galay-utils 是纯头文件库，无需编译。直接 include 即可使用：

```cmake
// CMakeLists.txt
find_package(galay-utils REQUIRED)
target_link_libraries(myapp PRIVATE galay::galay-utils)
```

### 构建选项

```text
-DBUILD_TESTS=ON/OFF
-DBUILD_MODULE_TESTS=ON/OFF
```

`BUILD_MODULE_TESTS` 需要 CMake >= 3.28，推荐 Ninja/Visual Studio 生成器。

## 依赖

C++23 编译器与 CMake 3.16+；无第三方强依赖。

Unix 平台会在接口目标上附加 `pthread`（Linux 额外 `dl`）。

## 项目地址

[https://github.com/gzj-creator/galay-utils](https://github.com/gzj-creator/galay-utils)

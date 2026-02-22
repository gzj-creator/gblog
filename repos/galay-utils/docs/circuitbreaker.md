# CircuitBreaker 模块

## 概述

CircuitBreaker 模块实现了熔断器模式，用于保护服务免受级联故障的影响。采用无锁原子变量实现，性能可达 10M ops/sec。

## 特性

- 无锁设计：使用原子变量和 CAS 操作实现状态转换
- 高性能：~10M ops/sec
- 线程安全：适合高并发和协程环境

## 主要功能

### 熔断器配置

```cpp
CircuitBreakerConfig config;
config.failureThreshold = 5;        // 连续失败5次后熔断
config.successThreshold = 3;        // 半开状态连续成功3次后恢复
config.resetTimeout = std::chrono::seconds(30); // 熔断30秒后进入半开状态

CircuitBreaker cb(config);
```

### 熔断器状态

```cpp
CircuitState state = cb.state();
// Closed: 关闭状态，允许请求
// Open: 开放状态，快速失败
// HalfOpen: 半开放状态，测试恢复

const char* stateStr = cb.stateString(); // "CLOSED", "OPEN", "HALF_OPEN"
```

### 请求处理

```cpp
// 方式1：手动控制
if (cb.allowRequest()) {
    try {
        // 执行请求
        cb.onSuccess();
    } catch (...) {
        cb.onFailure();
        throw;
    }
} else {
    // 熔断器开放，快速失败
}

// 方式2：使用 execute（自动处理成功/失败）
try {
    auto result = cb.execute([&]() {
        return doRequest();
    });
} catch (const std::runtime_error& e) {
    // 熔断器开放或请求失败
}

// 方式3：使用 executeWithFallback（带降级）
auto result = cb.executeWithFallback(
    [&]() { return doRequest(); },
    [&]() { return fallbackValue(); }
);
```

### 状态查询与控制

```cpp
size_t failures = cb.failureCount();  // 当前失败计数
size_t successes = cb.successCount(); // 当前成功计数

cb.reset();     // 重置为关闭状态
cb.forceOpen(); // 强制打开熔断器
```

## 状态转换

```text
     失败次数达到阈值
Closed ──────────────────> Open
   ^                         │
   │                         │ 超时后
   │ 成功次数达到阈值         v
   └─────────────────── HalfOpen
                             │
                             │ 发生失败
                             v
                           Open
```

## 性能

压测结果（8 线程，800K 操作）：~10M ops/sec

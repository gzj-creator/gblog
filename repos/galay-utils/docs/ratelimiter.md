# RateLimiter 模块

## 概述

RateLimiter 模块提供了多种速率限制算法，用于控制请求频率。所有限流器均采用无锁原子变量实现，支持协程异步接口。

## 特性

- 无锁设计：使用原子变量和 CAS 操作，高并发性能 3-4M ops/sec
- 协程支持：`acquire()` 返回 Awaitable，支持 `co_await` 和超时
- 依赖 galay-kernel 协程框架

## 主要功能

### 计数信号量

```cpp
CountingSemaphore sem(3); // 允许3个并发

// 非阻塞尝试
if (sem.tryAcquire(2)) {
    // 获取成功
    sem.release(2);
}

// 协程异步获取
co_await sem.acquire(2);
sem.release(2);

// 带超时
auto result = co_await sem.acquire(2).timeout(100ms);
if (!result) {
    // 超时
}
```

### 令牌桶

```cpp
TokenBucketLimiter bucket(100.0, 10); // 100 tokens/sec, 容量10

// 非阻塞尝试
if (bucket.tryAcquire(5)) {
    // 处理请求
}

// 协程异步获取
co_await bucket.acquire(5);

// 带超时
auto result = co_await bucket.acquire(5).timeout(100ms);
```

### 滑动窗口

```cpp
SlidingWindowLimiter window(5, std::chrono::milliseconds(100)); // 100ms内最多5个请求

// 非阻塞尝试
if (window.tryAcquire()) {
    // 处理请求
}

// 协程异步获取
co_await window.acquire();

// 带超时
auto result = co_await window.acquire().timeout(50ms);
```

### 漏桶

```cpp
LeakyBucketLimiter leaky(100.0, 10); // 100/sec 流出速率, 容量10

// 非阻塞尝试
if (leaky.tryAcquire()) {
    // 处理请求
}

// 协程异步获取
co_await leaky.acquire();
```

## 性能

压测结果（4 调度器，4000 协程）：

| 限流器 | 吞吐量 |
|--------|--------|
| CountingSemaphore | ~4.2M ops/sec |
| TokenBucketLimiter | ~3.1M ops/sec |
| SlidingWindowLimiter | ~4.1M ops/sec |

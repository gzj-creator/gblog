# 02-API索引

本文档提供所有模块的快速索引和 API 概览。详细文档请查看各模块的独立文档。

## 核心工具

### String 模块

字符串处理工具，提供分割、连接、修剪、转换等功能。

**主要 API:**

```cpp
namespace galay::utils {
    class StringUtils {
        // 分割和连接
        static std::vector<std::string> split(const std::string& str, char delimiter);
        static std::vector<std::string> split(const std::string& str, const std::string& delimiter);
        static std::string join(const std::vector<std::string>& parts, const std::string& separator);

        // 修剪
        static std::string trim(const std::string& str);
        static std::string trimLeft(const std::string& str);
        static std::string trimRight(const std::string& str);

        // 大小写转换
        static std::string toLower(const std::string& str);
        static std::string toUpper(const std::string& str);

        // 查找和检查
        static bool startsWith(const std::string& str, const std::string& prefix);
        static bool endsWith(const std::string& str, const std::string& suffix);
        static bool contains(const std::string& str, const std::string& substr);
        static bool isBlank(const std::string& str);

        // 替换
        static std::string replace(const std::string& str, const std::string& from, const std::string& to);
        static std::string replaceFirst(const std::string& str, const std::string& from, const std::string& to);

        // 计数
        static size_t count(const std::string& str, char ch);
        static size_t count(const std::string& str, const std::string& substr);

        // 十六进制
        static std::string toHex(const uint8_t* data, size_t len, bool uppercase = false);
        static std::vector<uint8_t> fromHex(const std::string& hex);
        static std::string toVisibleHex(const uint8_t* data, size_t len);

        // 验证
        static bool isInteger(const std::string& str);
        static bool isFloat(const std::string& str);

        // 格式化和解析
        static std::string format(const char* fmt, ...);
        template<typename T> static T parse(const std::string& str);
        template<typename T> static std::string toString(const T& value);
    };
}
```

**详细文档:** [string.md](string.md)

---

### Random 模块

高质量随机数生成器，线程安全的单例模式。

**主要 API:**

```cpp
namespace galay::utils {
    class Randomizer {
        static Randomizer& instance();

        // 随机整数
        int randomInt(int min, int max);

        // 随机浮点数
        double randomDouble(double min, double max);

        // 随机字符串
        std::string randomString(size_t length);
        std::string randomHex(size_t length);

        // UUID
        std::string uuid();

        // 随机字节
        void randomBytes(uint8_t* buffer, size_t length);
    };
}
```

**详细文档:** [random.md](random.md)

---

### System 模块

系统级功能，包括文件操作、时间、环境变量等。

**主要 API:**

```cpp
namespace galay::utils {
    class System {
        // 系统信息
        static size_t cpuCount();
        static size_t memorySize();
        static std::string hostname();
        static int pid();
        static std::string username();

        // 文件操作
        static bool fileExists(const std::string& path);
        static size_t fileSize(const std::string& path);
        static std::string readFile(const std::string& path);
        static bool writeFile(const std::string& path, const std::string& content);

        // 时间
        static int64_t timestamp();
        static std::string formatTime(int64_t timestamp, const std::string& format);

        // 环境变量
        static std::string getEnv(const std::string& name);
        static bool setEnv(const std::string& name, const std::string& value);
    };
}
```

**详细文档:** [system.md](system.md)

---

### TypeName 模块

编译期类型名称提取。

**主要 API:**

```cpp
namespace galay::utils {
    template<typename T>
    constexpr std::string_view typeName();
}
```

**详细文档:** [typename.md](typename.md)

---

## 数据结构

### TrieTree 模块

前缀树实现，高效的字符串查找。

**主要 API:**

```cpp
namespace galay::utils {
    class TrieTree {
        void insert(const std::string& word);
        bool search(const std::string& word) const;
        bool startsWith(const std::string& prefix) const;
        void remove(const std::string& word);
    };
}
```

**详细文档:** [trie.md](trie.md)

---

### ConsistentHash 模块

一致性哈希算法，支持虚拟节点。

**主要 API:**

```cpp
namespace galay::utils {
    template<typename T>
    class ConsistentHash {
        ConsistentHash(size_t virtualNodes = 150);
        void addNode(const T& node);
        void removeNode(const T& node);
        std::optional<T> getNode(const std::string& key) const;
    };
}
```

**详细文档:** [consistent_hash.md](consistent_hash.md)

---

### Mvcc 模块

多版本并发控制。

**主要 API:**

```cpp
namespace galay::utils {
    template<typename T>
    class Mvcc {
        void write(const T& value);
        std::optional<T> read() const;
        std::optional<T> readVersion(uint64_t version) const;
    };
}
```

**详细文档:** [mvcc.md](mvcc.md)

---

### Huffman 模块

霍夫曼编码/解码。

**主要 API:**

```cpp
namespace galay::utils {
    class Huffman {
        static std::string encode(const std::string& data);
        static std::string decode(const std::string& encoded);
    };
}
```

**详细文档:** [huffman.md](huffman.md)

---

### Algorithm 模块

常用算法实现。

**主要 API:**

```cpp
namespace galay::utils {
    // Base64
    class Base64 {
        static std::string encode(const std::string& data);
        static std::string decode(const std::string& encoded);
    };

    // MD5
    class MD5 {
        static std::string hash(const std::string& data);
    };

    // HMAC
    class HMAC {
        static std::string hmacSha256(const std::string& key, const std::string& data);
    };

    // MurmurHash3
    class MurmurHash3 {
        static uint32_t hash32(const void* key, int len, uint32_t seed = 0);
        static void hash128(const void* key, int len, uint32_t seed, void* out);
    };

    // Salt
    class Salt {
        static std::string generate(size_t length = 16);
        static std::string hashPassword(const std::string& password, const std::string& salt);
    };
}
```

---

## 并发编程

### Thread 模块

线程池和线程安全容器。

**主要 API:**

```cpp
namespace galay::utils {
    class ThreadPool {
        ThreadPool(size_t numThreads);

        template<typename F, typename... Args>
        auto addTask(F&& f, Args&&... args) -> std::future<decltype(f(args...))>;
    };

    class TaskWaiter {
        template<typename F, typename... Args>
        void addTask(ThreadPool& pool, F&& f, Args&&... args);

        void wait();
    };

    template<typename T>
    class ThreadSafeList {
        void pushBack(const T& value);
        void pushFront(const T& value);
        std::optional<T> popFront();
        std::optional<T> popBack();
        size_t size() const;
    };
}
```

**详细文档:** [thread.md](thread.md)

---

### Pool 模块

对象池和阻塞对象池。

**主要 API:**

```cpp
namespace galay::utils {
    template<typename T>
    class ObjectPool {
        ObjectPool(std::function<std::unique_ptr<T>()> factory, size_t size);

        std::unique_ptr<T> acquire();
        void release(std::unique_ptr<T> obj);
    };

    template<typename T>
    class BlockingObjectPool {
        BlockingObjectPool(std::function<std::unique_ptr<T>()> factory, size_t size);

        std::unique_ptr<T> acquire();
        void release(std::unique_ptr<T> obj);
    };
}
```

**详细文档:** [pool.md](pool.md)

---

## 网络与分布式

### RateLimiter 模块

多算法速率限制器，支持协程异步接口。

**主要 API:**

```cpp
namespace galay::utils {
    // 计数信号量
    class CountingSemaphore {
        CountingSemaphore(size_t maxCount);

        bool tryAcquire(size_t count = 1);
        void release(size_t count = 1);

        // 协程接口（需要 galay-kernel）
        CustomAwaitable<bool> acquire(size_t count = 1);
    };

    // 令牌桶
    class TokenBucketLimiter {
        TokenBucketLimiter(double rate, size_t capacity);

        bool tryAcquire(size_t tokens = 1);
        CustomAwaitable<bool> acquire(size_t tokens = 1);
    };

    // 滑动窗口
    class SlidingWindowLimiter {
        SlidingWindowLimiter(size_t maxRequests, std::chrono::milliseconds window);

        bool tryAcquire();
        CustomAwaitable<bool> acquire();
    };

    // 漏桶
    class LeakyBucketLimiter {
        LeakyBucketLimiter(double rate, size_t capacity);

        bool tryAcquire();
        CustomAwaitable<bool> acquire();
    };
}
```

**详细文档:** [ratelimiter.md](ratelimiter.md)

---

### CircuitBreaker 模块

熔断器模式实现，无锁原子设计。

**主要 API:**

```cpp
namespace galay::utils {
    struct CircuitBreakerConfig {
        size_t failureThreshold = 5;
        size_t successThreshold = 3;
        std::chrono::milliseconds resetTimeout = std::chrono::seconds(30);
    };

    enum class CircuitState {
        Closed,
        Open,
        HalfOpen
    };

    class CircuitBreaker {
        CircuitBreaker(const CircuitBreakerConfig& config);

        bool allowRequest();
        void onSuccess();
        void onFailure();

        CircuitState state() const;
        const char* stateString() const;

        template<typename F>
        auto execute(F&& func) -> decltype(func());

        template<typename F, typename Fallback>
        auto executeWithFallback(F&& func, Fallback&& fallback) -> decltype(func());

        void reset();
        void forceOpen();
    };
}
```

**详细文档:** [circuitbreaker.md](circuitbreaker.md)

---

### Balancer 模块

多种负载均衡算法。

**主要 API:**

```cpp
namespace galay::utils {
    // 轮询
    template<typename T>
    class RoundRobinLoadBalancer {
        RoundRobinLoadBalancer(const std::vector<T>& nodes);

        std::optional<T> select();
        void append(const T& node);
    };

    // 加权轮询
    template<typename T>
    class WeightRoundRobinLoadBalancer {
        WeightRoundRobinLoadBalancer(const std::vector<T>& nodes, const std::vector<uint32_t>& weights);

        std::optional<T> select();
    };

    // 随机
    template<typename T>
    class RandomLoadBalancer {
        RandomLoadBalancer(const std::vector<T>& nodes);

        std::optional<T> select();
        void append(const T& node);
    };

    // 加权随机
    template<typename T>
    class WeightedRandomLoadBalancer {
        WeightedRandomLoadBalancer(const std::vector<T>& nodes, const std::vector<uint32_t>& weights);

        std::optional<T> select();
    };
}
```

**详细文档:** [balancer.md](balancer.md)

---

## 应用框架

### App 模块

命令行参数解析。

**主要 API:**

```cpp
namespace galay::utils {
    class App {
        App(const std::string& name, const std::string& description);

        void addOption(const std::string& name, const std::string& description, bool required = false);
        void addFlag(const std::string& name, const std::string& description);

        bool parse(int argc, char* argv[]);

        std::string getOption(const std::string& name) const;
        bool hasFlag(const std::string& name) const;

        void printHelp() const;
    };
}
```

**详细文档:** [app.md](app.md)

---

### Parser 模块

配置文件解析（INI、环境变量）。

**主要 API:**

```cpp
namespace galay::utils {
    class IniParser {
        bool parse(const std::string& filename);

        std::string get(const std::string& section, const std::string& key) const;
        bool has(const std::string& section, const std::string& key) const;
    };

    class EnvParser {
        static std::string get(const std::string& key);
        static bool has(const std::string& key);
    };
}
```

**详细文档:** [parser.md](parser.md)

---

## 系统集成

### Process 模块

进程管理。

**主要 API:**

```cpp
namespace galay::utils {
    class Process {
        static int execute(const std::string& command);
        static std::string executeWithOutput(const std::string& command);
    };
}
```

**详细文档:** [process.md](process.md)

---

### Signal 模块

信号处理。

**主要 API:**

```cpp
namespace galay::utils {
    class SignalHandler {
        static void registerHandler(int signal, std::function<void(int)> handler);
        static void ignore(int signal);
        static void reset(int signal);
    };
}
```

**详细文档:** [signal.md](signal.md)

---

### BackTrace 模块

栈追踪。

**主要 API:**

```cpp
namespace galay::utils {
    class BackTrace {
        static std::vector<std::string> capture(size_t skip = 0);
        static void print(std::ostream& os = std::cerr);
    };
}
```

**详细文档:** [backtrace.md](backtrace.md)

---

## 快速查找

### 按功能分类

**字符串处理:**
- [String](string.md) - 字符串工具

**随机数:**
- [Random](random.md) - 随机数生成

**系统操作:**
- [System](system.md) - 系统信息和文件操作
- [Process](process.md) - 进程管理
- [Signal](signal.md) - 信号处理
- [BackTrace](backtrace.md) - 栈追踪

**数据结构:**
- [TrieTree](trie.md) - 前缀树
- [ConsistentHash](consistent_hash.md) - 一致性哈希
- [Mvcc](mvcc.md) - 多版本并发控制

**编码压缩:**
- [Huffman](huffman.md) - 霍夫曼编码
- Algorithm - Base64, MD5, HMAC, MurmurHash3

**并发编程:**
- [Thread](thread.md) - 线程池
- [Pool](pool.md) - 对象池

**网络分布式:**
- [RateLimiter](ratelimiter.md) - 速率限制
- [CircuitBreaker](circuitbreaker.md) - 熔断器
- [Balancer](balancer.md) - 负载均衡

**应用框架:**
- [App](app.md) - 命令行参数
- [Parser](parser.md) - 配置解析

**工具:**
- [TypeName](typename.md) - 类型名称

### 按使用场景

**Web 服务:**
- RateLimiter - 限流
- CircuitBreaker - 熔断
- Balancer - 负载均衡
- ThreadPool - 并发处理

**数据处理:**
- String - 字符串处理
- Huffman - 数据压缩
- Algorithm - 编码和哈希

**系统工具:**
- System - 系统信息
- Process - 进程管理
- Signal - 信号处理
- BackTrace - 调试

**配置管理:**
- Parser - 配置文件
- App - 命令行参数

**高性能场景:**
- ObjectPool - 对象复用
- ConsistentHash - 分布式缓存
- Mvcc - 并发控制

## 性能参考

| 模块 | 操作 | 性能 |
|------|------|------|
| CircuitBreaker | allowRequest | ~10M ops/sec |
| RateLimiter | tryAcquire | ~3-4M ops/sec |
| StringUtils | split | ~1M ops/sec |
| Randomizer | randomInt | ~10M ops/sec |
| ConsistentHash | getNode | ~1M ops/sec |

## 线程安全性

| 模块 | 线程安全 | 说明 |
|------|----------|------|
| String | 是 | 无状态静态方法 |
| Random | 是 | 内部使用互斥锁 |
| System | 部分 | 读操作安全，写操作需外部同步 |
| Thread | 是 | 线程池和线程安全容器 |
| Pool | 是 | 内部使用互斥锁 |
| RateLimiter | 是 | 无锁原子操作 |
| CircuitBreaker | 是 | 无锁原子操作 |
| Balancer | 部分 | RoundRobin 和 Random 安全 |
| TrieTree | 否 | 需外部同步 |
| ConsistentHash | 否 | 需外部同步 |
| Mvcc | 是 | 多版本并发控制 |

## 依赖关系

```text
RateLimiter (协程接口) ──> galay-kernel
其他所有模块 ──> C++20 标准库（无外部依赖）
```

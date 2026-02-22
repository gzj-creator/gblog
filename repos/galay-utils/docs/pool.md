# Pool 模块

## 概述

Pool 模块提供了对象池功能，用于高效的对象复用，减少内存分配开销。

## 主要功能

### 对象池

```cpp
ObjectPool<std::string> pool(5, 10); // 初始5个对象，最大10个

// 获取对象
auto obj1 = pool.acquire();
*obj1 = "Hello";

// 对象自动返回池中
```

### 阻塞对象池

```cpp
BlockingObjectPool<int> pool(3); // 容量为3

// 获取对象（如果池空会阻塞）
auto obj = pool.acquire();

// 对象返回池中
```

# Balancer 模块

## 概述

Balancer 模块提供了多种负载均衡算法的实现，支持轮询、随机和加权调度策略。

## 主要功能

### 轮询负载均衡器 (RoundRobinLoadBalancer)

线程安全的轮询调度算法。

```cpp
#include "galay-utils/galay-utils.hpp"

std::vector<std::string> nodes = {"node1", "node2", "node3"};
galay::utils::RoundRobinLoadBalancer<std::string> balancer(nodes);

// 选择节点
auto selected = balancer.select(); // 返回可选值
if (selected) {
    std::cout << "Selected: " << *selected << std::endl;
}

// 添加新节点
balancer.append("node4");
```

### 加权轮询负载均衡器 (WeightRoundRobinLoadBalancer)

基于权重的轮询调度，确保高权重节点获得更多请求。

```cpp
std::vector<std::string> nodes = {"node1", "node2", "node3"};
std::vector<uint32_t> weights = {3, 2, 1}; // 权重比例 3:2:1

galay::utils::WeightRoundRobinLoadBalancer<std::string> balancer(nodes, weights);

// 选择节点 (node1会被选择3次, node2选择2次, node3选择1次，然后重复)
auto selected = balancer.select();
```

### 随机负载均衡器 (RandomLoadBalancer)

线程安全的随机调度算法。

```cpp
std::vector<std::string> nodes = {"node1", "node2", "node3"};
galay::utils::RandomLoadBalancer<std::string> balancer(nodes);

// 随机选择节点
auto selected = balancer.select();
```

### 加权随机负载均衡器 (WeightedRandomLoadBalancer)

基于权重的随机调度，权重越高被选中的概率越大。

```cpp
std::vector<std::string> nodes = {"node1", "node2", "node3"};
std::vector<uint32_t> weights = {30, 20, 10}; // 权重值

galay::utils::WeightedRandomLoadBalancer<std::string> balancer(nodes, weights);

// 加权随机选择
auto selected = balancer.select();
```

## 算法说明

### 轮询算法
- **RoundRobin**: 依次循环选择每个节点
- **WeightRoundRobin**: 基于权重进行轮询，确保权重比例

### 随机算法
- **Random**: 完全随机选择
- **WeightedRandom**: 根据权重随机选择，权重越大选中概率越高

## 线程安全

- `RoundRobinLoadBalancer`: 线程安全，使用原子操作
- `WeightRoundRobinLoadBalancer`: 非线程安全，适用于单线程环境
- `RandomLoadBalancer`: 线程安全，每个实例有独立随机数生成器
- `WeightedRandomLoadBalancer`: 线程安全，使用内部随机数生成器

## 性能特性

- **内存效率**: 所有算法都使用连续内存存储节点
- **缓存友好**: WeightRoundRobin使用64字节对齐避免伪共享
- **零拷贝**: 节点选择返回引用或可选值

## 使用建议

1. **高并发场景**: 使用 `RoundRobinLoadBalancer` 或 `RandomLoadBalancer`
2. **权重调度**: 使用 `WeightRoundRobinLoadBalancer` 或 `WeightedRandomLoadBalancer`
3. **简单负载均衡**: 使用 `RoundRobinLoadBalancer`
4. **动态扩容**: 所有均衡器都支持运行时添加新节点

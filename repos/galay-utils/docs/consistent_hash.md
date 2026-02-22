# ConsistentHash 模块

## 概述

ConsistentHash 模块实现了分布式系统中的一致性哈希算法，用于负载均衡和数据分片。

## 主要功能

### 创建哈希环

```cpp
ConsistentHash hash(100); // 每个节点100个虚拟节点

// 添加节点
hash.addNode({"node1", "192.168.1.1:8080", 1}); // 权重1
hash.addNode({"node2", "192.168.1.2:8080", 2}); // 权重2
```

### 获取节点

```cpp
// 获取单个节点
auto node = hash.getNode("key");

// 获取多个节点（用于复制）
auto nodes = hash.getNodes("key", 3);
```

### 节点管理

```cpp
// 移除节点
hash.removeNode("node1");

// 查询节点数量
size_t count = hash.nodeCount();
size_t virtualCount = hash.virtualNodeCount();
```

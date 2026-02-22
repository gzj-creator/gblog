# MVCC 模块

## 概述

MVCC 模块实现了多版本并发控制，用于支持事务的并发访问。

## 主要功能

### MVCC容器

```cpp
Mvcc<std::string> mvcc;

// 写入新版本
Version v1 = mvcc.putValue("value1");
Version v2 = mvcc.putValue("value2");

// 读取当前版本
const std::string* current = mvcc.getCurrentValue();

// 读取指定版本
const std::string* value = mvcc.getValue(v1);
```

### 快照

```cpp
Snapshot snapshot(v1);
const std::string* snapValue = snapshot.read(mvcc);
```

### 事务

```cpp
Transaction<std::string> txn(mvcc);

// 读取
const std::string* readVal = txn.read();

// 写入
txn.write(std::make_unique<std::string>("new_value"));

// 提交
bool success = txn.commit();
```

### 垃圾回收

```cpp
mvcc.gc(2); // 保留最近2个版本
```

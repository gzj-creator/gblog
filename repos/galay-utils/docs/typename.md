# TypeName 模块

## 概述

TypeName 模块提供了运行时类型名称获取功能。

## 主要功能

### 类型名称获取

```cpp
// 基本类型
std::string intName = getTypeName<int>();        // "int"
std::string strName = getTypeName<std::string>(); // "std::string" 或类似

// 容器类型
std::vector<int> vec;
std::string vecName = getTypeName(vec); // 包含"vector"的字符串
```

# BackTrace 模块

## 概述

BackTrace 模块提供了栈追踪功能，用于调试和错误诊断。

## 主要功能

### 栈追踪

```cpp
// 获取栈帧
auto frames = BackTrace::getStackTrace(10, 0);

// 获取栈追踪字符串
std::string trace = BackTrace::getStackTraceString(5, 0);
std::cout << trace << std::endl;
```

# Process 模块

## 概述

Process 模块提供了进程管理功能，包括进程信息获取和命令执行。

## 主要功能

### 进程信息

```cpp
// 当前进程ID
ProcessId pid = Process::currentId();

// 父进程ID
ProcessId ppid = Process::parentId();

// 检查进程是否运行
bool running = Process::isRunning(pid);
```

### 命令执行

```cpp
// 执行命令并获取输出
auto [status, output] = Process::executeWithOutput("echo hello");

if (status.success()) {
    std::cout << "Output: " << output << std::endl;
}
```

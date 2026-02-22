# System 模块

## 概述

System 模块提供了跨平台的系统级功能，包括时间处理、文件操作、环境变量、进程信息等。

## 主要功能

### 时间函数

```cpp
// 获取当前时间戳
int64_t ms = System::currentTimeMs();
int64_t us = System::currentTimeUs();
int64_t ns = System::currentTimeNs();

// 获取格式化的时间字符串
std::string gmt = System::currentGMTTime();      // GMT时间
std::string local = System::currentLocalTime();  // 本地时间

// 自定义格式的时间
std::string custom = System::formatTime(timestamp, "%Y-%m-%d %H:%M:%S");
```

### 文件操作

```cpp
// 读取文件
auto content = System::readFile("/path/to/file.txt");
if (content) {
    std::cout << *content << std::endl;
}

// 写入文件
bool success = System::writeFile("/path/to/file.txt", "Hello, World!");

// 文件信息
bool exists = System::fileExists("/path/to/file.txt");
size_t size = System::fileSize("/path/to/file.txt");

// 删除文件
bool deleted = System::remove("/path/to/file.txt");
```

### 目录操作

```cpp
// 创建目录
bool created = System::createDirectory("/path/to/dir");

// 检查目录是否存在
bool isDir = System::isDirectory("/path/to/dir");

// 删除目录
bool removed = System::remove("/path/to/dir");
```

### 环境变量

```cpp
// 设置环境变量
System::setEnv("MY_VAR", "value");

// 获取环境变量
auto value = System::getEnv("MY_VAR");
auto defaultValue = System::getEnv("NON_EXISTENT", "default");

// 取消设置环境变量
System::unsetEnv("MY_VAR");
```

### 系统信息

```cpp
// CPU核心数
int cpuCount = System::cpuCount();

// 主机名
std::string hostname = System::hostname();

// 当前工作目录
std::string cwd = System::currentDir();
```

### 路径操作

```cpp
// 获取绝对路径
std::string absPath = System::absolutePath("relative/path");

// 获取路径的目录部分
std::string dir = System::dirname("/path/to/file.txt");

// 获取文件名部分
std::string filename = System::basename("/path/to/file.txt");

// 获取文件扩展名
std::string ext = System::extension("/path/to/file.txt");
```

### 进程信息

```cpp
// 当前进程ID
pid_t pid = System::currentProcessId();

// 父进程ID
pid_t ppid = System::parentProcessId();

// 检查进程是否运行
bool running = System::isProcessRunning(pid);
```

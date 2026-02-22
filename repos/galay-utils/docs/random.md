# Random 模块

## 概述

Random 模块提供了高质量的随机数生成功能，包括整数范围、浮点数范围、随机字符串、UUID生成等。

## 主要功能

### 随机数生成器

```cpp
auto& rng = Randomizer::instance();
```

### 整数范围随机数

```cpp
// 生成10-20之间的随机整数
int value = rng.randomInt(10, 20);
```

### 浮点数范围随机数

```cpp
// 生成0.0-1.0之间的随机浮点数
double value = rng.randomDouble(0.0, 1.0);
```

### 随机字符串

```cpp
// 生成10位随机字符串
std::string str = rng.randomString(10);
```

### 随机十六进制字符串

```cpp
// 生成8位随机十六进制字符串
std::string hex = rng.randomHex(8);
```

### UUID生成

```cpp
// 生成UUID v4
std::string uuid = rng.uuid(); // 格式: xxxxxxxx-xxxx-4xxx-xxxx-xxxxxxxxxxxx
```

### 随机字节

```cpp
uint8_t buffer[16];
rng.randomBytes(buffer, 16);
```

# String 模块

## 概述

String 模块提供了常用的字符串处理功能，包括分割、连接、修剪、转换、大小写处理、查找替换等操作。

## 主要功能

### 字符串分割

```cpp
// 按字符分割
std::vector<std::string> parts = StringUtils::split("a,b,c", ',');

// 按字符串分割
parts = StringUtils::split("hello world test", " ");

// 尊重引号的分割
parts = StringUtils::splitRespectQuotes("a,'b,c',d", ',', '\'');
```

### 字符串连接

```cpp
std::vector<std::string> parts = {"a", "b", "c"};
std::string result = StringUtils::join(parts, "-"); // "a-b-c"
```

### 字符串修剪

```cpp
std::string trimmed = StringUtils::trim("  hello  ");     // "hello"
std::string left = StringUtils::trimLeft("  hello");      // "hello"
std::string right = StringUtils::trimRight("hello  ");    // "hello"
```

### 大小写转换

```cpp
std::string lower = StringUtils::toLower("HELLO");  // "hello"
std::string upper = StringUtils::toUpper("hello");  // "HELLO"
```

### 字符串检查

```cpp
bool starts = StringUtils::startsWith("hello world", "hello");     // true
bool ends = StringUtils::endsWith("hello world", "world");         // true
bool contains = StringUtils::contains("hello world", "lo wo");      // true
bool blank = StringUtils::isBlank("   ");                          // true
```

### 查找和替换

```cpp
std::string replaced = StringUtils::replace("aaa", "a", "b");       // "bbb"
std::string first = StringUtils::replaceFirst("aaa", "a", "b");     // "baa"
```

### 计数

```cpp
size_t count = StringUtils::count("hello", 'l');    // 2
size_t substrCount = StringUtils::count("ababa", "ab"); // 2
```

### 十六进制转换

```cpp
uint8_t data[] = {0xDE, 0xAD, 0xBE, 0xEF};
std::string hex = StringUtils::toHex(data, 4, true);        // "DEADBEEF"
std::vector<uint8_t> bytes = StringUtils::fromHex("DEADBEEF");
std::string visible = StringUtils::toVisibleHex(data, 4);   // "DE AD BE EF"
```

### 数值验证

```cpp
bool isInt = StringUtils::isInteger("123");     // true
bool isFloat = StringUtils::isFloat("3.14");    // true
```

### 格式化和解析

```cpp
std::string formatted = StringUtils::format("Hello %s, %d", "World", 42); // "Hello World, 42"

int value = StringUtils::parse<int>("42");              // 42
double dvalue = StringUtils::parse<double>("3.14");     // 3.14

std::string str = StringUtils::toString(123);           // "123"
```

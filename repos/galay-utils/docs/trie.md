# Trie 模块

## 概述

Trie 模块实现了前缀树（Trie树）数据结构，用于高效的字符串查找和前缀匹配。

## 主要功能

### Trie树操作

```cpp
TrieTree trie;

// 插入单词
trie.add("hello");
trie.add("help");
trie.add("world");

// 查询
bool exists = trie.contains("hello");
size_t count = trie.query("hello"); // 获取出现次数

// 前缀匹配
bool hasPrefix = trie.startsWith("hel");
auto words = trie.getWordsWithPrefix("hel");

// 删除
bool removed = trie.remove("hello");
```

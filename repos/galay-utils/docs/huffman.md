# Huffman 模块

## 概述

Huffman 模块实现了霍夫曼编码算法，用于数据压缩。

## 主要功能

### 霍夫曼编码

```cpp
std::vector<char> data = {'a', 'a', 'a', 'b', 'b', 'c'};

// 构建编码表
auto table = HuffmanBuilder<char>::buildFromData(data);

// 创建编码器
HuffmanEncoder<char> encoder(table);
encoder.encode(data);
auto encoded = encoder.finish();

// 创建解码器
HuffmanDecoder<char> decoder(table, 1, 8);
auto decoded = decoder.decode(encoded, data.size());
```

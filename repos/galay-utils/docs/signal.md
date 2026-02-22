# Signal 模块

## 概述

Signal 模块提供了信号处理功能，支持自定义信号处理器。

## 主要功能

### 信号处理器

```cpp
auto& handler = SignalHandler::instance();

// 设置信号处理器
bool signalReceived = false;
handler.setHandler(SIGUSR1, [&signalReceived](int sig) {
    signalReceived = true;
});

// 发送信号测试
raise(SIGUSR1);

// 移除处理器
handler.removeHandler(SIGUSR1);
```

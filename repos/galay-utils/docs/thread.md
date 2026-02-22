# Thread 模块

## 概述

Thread 模块提供了线程池和线程安全的容器，支持任务调度和并发编程。

## 主要功能

### 线程池

```cpp
ThreadPool pool(4); // 创建4线程的线程池

// 添加任务
auto future = pool.addTask([]() {
    return 42;
});

// 获取结果
int result = future.get();
```

### 任务等待器

```cpp
TaskWaiter waiter;

// 添加多个任务
for (int i = 0; i < 5; ++i) {
    waiter.addTask(pool, [i]() {
        std::cout << "Task " << i << std::endl;
    });
}

// 等待所有任务完成
waiter.wait();
```

### 线程安全容器

```cpp
ThreadSafeList<int> list;

list.pushBack(1);
list.pushBack(2);
list.pushFront(0);

auto front = list.popFront(); // 0
auto back = list.popBack();   // 2
```

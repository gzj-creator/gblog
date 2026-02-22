# App 模块

## 概述

App 模块提供了命令行参数解析功能，支持位置参数、命名参数、标志等。

## 主要功能

### 应用定义

```cpp
App app("myapp", "My application description");

// 添加参数
app.addArg(Arg("name", "User name").shortName('n').required());
app.addArg(Arg("count", "Count").shortName('c').type(ArgType::Int).defaultValue(1));
app.addArg(Arg("verbose", "Verbose mode").shortName('v').flag());

// 设置回调
app.callback([](Cmd& cmd) {
    std::string name = cmd.getAs<std::string>("name");
    int count = cmd.getAs<int>("count");
    bool verbose = cmd.getAs<bool>("verbose");

    // 处理逻辑
    return 0;
});

// 运行应用
const char* argv[] = {"myapp", "--name", "John", "-c", "5", "-v"};
return app.run(6, argv);
```

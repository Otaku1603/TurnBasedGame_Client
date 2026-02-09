# TurnBasedGame-Client

## 简介

本项目是基于 Unity 2022 开发的一款回合制策略游戏客户端。它包含完整的用户认证、大厅社交功能（商店、背包、排行榜、好友）、匹配对战以及核心的战斗逻辑表现。

## 技术栈

- **引擎**: Unity 2022.3+
- **UI**: UGUI (Legacy)
- **动画**: DOTween
- **数据序列化**:
  - **网络**: Google.Protobuf (用于 TCP 实时通信)
  - **HTTP**: Newtonsoft.Json (用于 Web API)
- **核心依赖**:
  - `DG.Tweening`
  - `Google.Protobuf`
  - `Newtonsoft.Json`

## 设计亮点

### 1. 程序化 UI (Programmatic UI)

为降低对美术资源的硬性依赖，便于快速原型开发，项目内置了一套程序化资源生成机制。

- **核心模块**: `ResourceManager`
- **实现方式**:
  - **动态生成纯色精灵**: 当 `ResourceManager` 无法从 `Resources` 文件夹加载到指定图标（如道具、头像）时，它会根据配置（`ColorConfig`）动态创建一个纯色 `Texture2D` 并生成 `Sprite` 作为兜底显示。例如，药水显示为蓝色方块，战士头像为红色方块。
  - **精灵对象池**: 所有动态生成的纯色精灵都通过 `GetOrCreateColorSprite` 方法进行管理。该方法使用颜色和尺寸生成唯一键，确保相同颜色的精灵只被创建一次，并被缓存复用，有效减少了纹理内存开销。
  - **动态生成头像框**: `GetFrameSprite` 方法在加载不到预设图片时，会程序化地绘制一个带颜色的镂空矩形作为头像框，边框颜色同样由 `ColorConfig` 根据配置路径中的关键字（如 `gold`, `silver`）决定。

这种设计使得即使在完全没有美术资源的情况下，游戏的核心功能和 UI 逻辑依然能够正常运行和测试。

### 2. 鲁棒的战斗动画同步机制

回合制战斗中，网络延迟或快速的连续事件（如反击、连击）可能导致客户端动画表现与服务器逻辑状态不一致，甚至出现动画被中断、状态卡死等问题。本项目通过基于消息队列的机制彻底解决了这一难题。

- **核心模块**: `BattleController`
- **核心组件**: `Queue<BattleUpdateResponse> _updateQueue`
- **工作流程**:
  1.  **入队 (Enqueue)**: `BattleService` 收到任何 `BattleUpdateResponse` 网络消息后，不会立即处理，而是调用 `BattleController.EnqueueBattleUpdate` 将其放入一个先进先出（FIFO）的队列 `_updateQueue` 中。
  2.  **加锁处理**: `BattleController` 维护一个布尔锁 `_isProcessingQueue`。当队列开始被处理时，此锁被置为 `true`，防止并发执行。
  3.  **顺序执行**: 一个名为 `ProcessUpdateQueue` 的协程负责从队列中取出消息。它一次只取一条，然后启动 `PlayAnimationSequence` 协程播放完整的动画序列（如：角色移动 -> 攻击特效 -> 伤害飘字 -> 受击反馈 -> 血条更新）。
  4.  **等待动画完成**: 最关键的一步，`ProcessUpdateQueue` 协程会 `yield return` 等待 `PlayAnimationSequence` 协程完全执行完毕。
  5.  **解锁与循环**: 只有在动画播放结束后，协程才会继续循环，从队列中取出下一条消息进行处理。如果队列为空，则将 `_isProcessingQueue` 锁置为 `false`，等待下一次消息的到来。

这个设计确保了无论网络消息以多快的速度到达，客户端的动画表现永远是**严格按照服务器下发的顺序、一个接一个地、完整地**播放，从而杜绝了任何视觉上的状态错乱和逻辑死锁。

## 3. 架构概述

客户端采用经典的分层架构，旨在实现高内聚、低耦合，便于模块化开发和维护。

-   **View (视图层)**:
    -   职责：负责所有 UI 元素的显示、更新和动画表现。只关心“如何展示”，不关心“为什么展示”。
    -   实现：继承自 `BaseView` 的 `MonoBehaviour` 脚本，通过 `AutoBindUI` 反射机制自动绑定节点，减少手动拖拽。如 `BattleView` 负责播放战斗动画，`MainSceneView` 负责切换大厅面板。

-   **Controller (控制层)**:
    -   职责：作为 `View` 和 `Service` 之间的桥梁。监听 `View` 的用户输入事件（如按钮点击），调用 `Service` 层处理业务逻辑；同时订阅 `Service` 层的事件，在收到回调或网络推送后，驱动 `View` 层更新界面。
    -   实现：场景级的 `MonoBehaviour`，如 `LoginController`, `MainSceneController`, `BattleController`。

-   **Service (服务层)**:
    -   职责：处理所有与后端交互的业务逻辑。封装 HTTP 请求和 TCP 消息的收发，为 `Controller` 层提供简洁的、面向业务的接口（如 `AuthService.Login()`）。同时，它将收到的网络数据转换为 C# 事件，供 `Controller` 订阅。
    -   实现：纯 C# 单例类，如 `AuthService`, `BattleService`, `ConfigManager`。

-   **Network (网络层)**:
    -   职责：提供底层的网络通信能力。`NetworkManager` 负责维护 TCP 长连接、处理 Protobuf 的序列化/反序列化、解决粘包/拆包问题，并使用线程安全的队列将网络线程收到的消息派发到 Unity 主线程。

-   **Model (数据模型层)**:
    -   职责：定义应用程序所需的数据结构。包括与服务器 API 对应的 HTTP 模型、Protobuf 生成的网络消息类，以及客户端内部使用的 ViewModel。
    -   实现：纯 C# 类（POCO）和 Protobuf 生成的代码。

-   **Core (核心层)**:
    -   职责：提供全局性的、与具体业务无关的基础功能。
    -   实现：`GameEntry` 作为游戏入口和心跳管理器，`AppConfig` 集中管理服务器地址等配置。

## 4. 核心模块详解

-   **`Core`**:
    -   `GameEntry`: 游戏入口 `MonoBehaviour`，`DontDestroyOnLoad`，负责启动和维持 `NetworkManager` 的心跳。
    -   `AppConfig`: 静态类，存储服务器 IP 和端口，方便打包时修改。

-   **`Network`**:
    -   `NetworkManager`: 封装了 `TcpClient`，使用独立的接收线程（`ReceiveLoop`）防止主线程阻塞。通过 `ConcurrentQueue` 实现跨线程消息传递。采用 "长度前缀 + Protobuf 消息体" 的方式解决粘包问题。

-   **`Services`**:
    -   `AuthService`: 处理 HTTP 注册/登录，获取 Token，然后驱动 `NetworkManager` 建立 TCP 连接并发送 Proto 登录握手。
    -   `BattleService`: 封装所有战斗相关的 Proto 消息收发，并将 `BattleStart`, `BattleUpdate` 等消息转化为 C# 事件。
    -   `ConfigManager`: 在游戏启动时通过 HTTP 异步加载所有静态配置表（技能、道具等），并缓存在字典中供全局访问。
    -   `ShopService`/`SocialService`: 封装与商店、社交功能相关的 HTTP API 请求。

-   **`Controller`**:
    -   `LoginController`: 协调 `LoginView` 和 `AuthService`，处理登录、注册、断线重连逻辑。
    -   `MainSceneController`: 大厅总控制器，管理商店、背包、排行榜等所有功能的打开、数据刷新和UI交互。
    -   `BattleController`: 战斗总控制器，管理战斗状态机。其核心是上文提到的**动画同步队列**，确保战斗表现的正确性。

-   **`View`**:
    -   `BaseView`: 提供了 `AutoBindUI` 功能，子类只需定义与场景中物体同名的 `public` 字段即可自动完成赋值。
    -   `BattleView`: 提供了所有战斗动画的协程方法（如 `PlayAttackAnim`），这些方法使用 DOTween 实现，并通过返回 `IEnumerator` 来支持时序控制。

## 5. 项目启动指南

1.  在 `Core/AppConfig.cs` 中，修改 `DEFAULT_IP`（也可以选择在客户端实例中点击`Dev`按钮自定义IP或URL）, `HTTP_PORT`, `TCP_PORT` 为您本地或远程服务器的正确地址。
2.  打开 `LoginScene` 场景。
3.  点击 Unity 编辑器的 Play 按钮。
4.  客户端将首先尝试连接服务器加载配置表，成功后显示登录界面。
5.  注册账号或使用已有账号登录即可进入游戏大厅。
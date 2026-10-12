# Jev Phone

**多模态决策驱动的三端视觉交互通道。**

[中文](README.md) · [English](README.en.md)

模型只选择当前画面的候选编号，SDK 将编号绑定到真实区域并完成点击。供已有 AI、Planner、测试系统和脚本独立接入，支持 Android、iOS、HarmonyOS 的单步与连续步骤执行。

<p align="center"><b>Android · iOS · HarmonyOS</b> ／ 真机 · 虚拟机<br>独立 Python SDK · Demo 与 SDK 同一执行流程 · MIT</p>

[执行演示](#执行演示) · [为什么做](#为什么做) · [核心机制](#核心机制) · [毫秒级处理与计时](#毫秒级处理与计时) · [快速接入](#快速接入)

## 执行演示

### 选择困难并开始挑战

真实安卓手机：打开练习设置 → 选择最右侧橙色困难卡片 → 开始挑战。最终进入困难题目。原速连续录制，右上角秒表按执行经过时间连续更新。

![困难挑战三步演示](docs/media/demo-hard-challenge.gif)

| 操作 | 模型请求往返 |
|---|---:|
| 打开练习设置 | 1944.83ms |
| 选择困难 | 1025.65ms |
| 开始挑战 | 765.28ms |

整段执行 **6570.28ms**，包含采集、候选生成、模型请求、点击及步骤衔接。[原速视频](docs/media/demo-hard-challenge.mp4) · [计时记录](docs/media/demo-hard-challenge.json)

### 浏览章节并打开设置

依次点击“集合间的基本关系” → “集合的基本运算” → 右上方黄色铅笔，打开练习设置。

![章节切换三步演示](docs/media/demo-section-switch.gif)

三步模型请求往返分别 **827.78ms / 693.05ms / 1999.53ms**。两段演示每步模型请求均低于2秒；这是模型请求往返口径，不是完整步骤耗时。[原速视频](docs/media/demo-section-switch.mp4) · [计时记录](docs/media/demo-section-switch.json)

## 为什么做

已有系统往往已经决定“下一步做什么”，还需要一个可复用的通道完成“当前画面中点哪里”。Jev Phone 承接这一段：将语义目标、可见区域和设备动作绑定起来，同时保留调用方已有的规划、缓存与业务判断。

| 需要承接的环节 | 组件如何处理 |
|---|---|
| 系统树能给出位置，却不一定表达图标或画面语义 | 结合树的区域边界与截图的视觉信息生成候选。 |
| 模型理解了目标，结果还需要对应真实可执行区域 | 让模型选择区域编号，SDK 依据当帧区域映射坐标并执行。 |
| 三端层级、尺寸与坐标单位不同 | 通过平台适配统一调用，iOS 处理截图 pixel 与 WDA point 映射。 |
| 调好的设备通道难以从完整框架中单独复用 | 将 AI Phone V3 已调好的采集、点击和步骤衔接承接为独立 SDK；外部系统继续掌握规划与缓存。 |
| 连续点击后，下一页面可能仍在动画或加载 | 步骤间复用 V3 图片对比与末帧，避免下一步立即使用过渡画面。 |

设备通道与步骤衔接沿用已经调好的 V3 实现，SDK 不依赖 AI Phone 框架。

![视觉目标定位与设备动作绑定](docs/media/modules/core.png)

## 核心机制

**当前目标 → 系统树与截图 → 区域编号 → 模型有限选择 → 平台点击。**

模型返回候选编号、`NOT_FOUND` 或 `UNCERTAIN`；当前目标、候选属性和编号图共同组成该步输入。编号绑定当帧区域，SDK 执行区域中心点击。

![区域标注与有限动作空间](docs/media/modules/flow.png)

系统节点提供几何区域与属性；截图补充文字、图标和外观语义。下面的官网示意展示：节点文字为空时，仍可依据画面中的头像选择对应区域。

![几何约束与视觉语义融合](docs/media/modules/grounding.png)

### 职责与连续执行

调用方决定目标、顺序和业务结果；SDK 负责采集、候选、模型选择、点击与步骤衔接，并返回事件、编号图、坐标和毫秒计时。驱动点击返回不等于业务结果已确认。

![调用方与组件职责边界](docs/media/modules/responsibility.png)

`click(target)` 执行一个点击；`run(text)` 按中英文逗号、分号、句号、问号、感叹号及换行拆步，最多20步。每步只向模型传入当前目标，定位或点击失败停止后续步骤。Demo 使用同一 `run()` 流程。

## 三端适配

三端真机／虚拟机均已贯通。官网原始卡片与目标区域分别展示；点击原图链接可查看完整编号图。原始证据分别来自安卓真机、iOS虚拟机、鸿蒙虚拟机，支持范围与单张图片来源分别标明。

### Android · 真机／虚拟机

![Android官网卡片](docs/media/modules/android.png)

![Android目标区域放大](docs/media/modules/android-detail.png)

[完整编号图](docs/media/android-grounding.png) · UiAutomator2 原生截图、系统树与坐标点击。

### iOS · 真机／虚拟机

![iOS官网卡片](docs/media/modules/ios.png)

![iOS目标区域放大](docs/media/modules/ios-detail.png)

[完整编号图](docs/media/ios-grounding.png) · WDA 按需截图、XCTest 层级与 pixel/point 映射。

### HarmonyOS · 真机／虚拟机

![HarmonyOS官网卡片](docs/media/modules/harmony.png)

![HarmonyOS目标区域放大](docs/media/modules/harmony-detail.png)

[完整编号图](docs/media/harmony-grounding.png) · 原生截图、UITest 层级与直接点击回执。

## 毫秒级处理与计时

**毫秒级指组件通道处理的分段计时，不代表所有点击在几十毫秒内完成。** 模型网络请求、设备采集、点击与步骤衔接分别记录，不能混为一个速度指标。

![官网毫秒级处理与分段计时](docs/media/modules/timing.png)

官网中的 **15–50ms** 是前期实验的本地候选处理、画框与编码；**620ms** 是安卓非模型整轮实测中位，**493–729ms** 是同一导航样本9轮范围。它们不包含模型请求、初始化与步骤衔接，不是所有平台或页面的速度保证。上方两段演示另给出当前 SDK 的真实模型往返和整段执行记录。

单步点击链路 = 模型请求往返 + 组件自身处理。多步总时长还包括步骤间图片对比；最后一步不再追加衔接等待，也不逐步补拍结束截图。

| 平台 | V3 对比采样额外间隔 |
|---|---:|
| Android | 100ms |
| iOS | 200ms |
| HarmonyOS | 0ms |

截图本身仍有耗时。三端复用对比末帧；对比预算耗尽时沿用 V3 返回最后一帧继续，不额外拦截。参数与执行流程保持已调版本。

## 快速接入

Python 3.10+，从源码或 wheel 安装；尚未发布到 PyPI。先准备平台设备服务及模型 Key。

```sh
git clone https://github.com/dongxinsuperman/jev-phone.git
cd jev-phone
python3 -m venv .venv
.venv/bin/pip install -e '.[android]'
# iOS: .venv/bin/pip install -e .
# HarmonyOS: .venv/bin/pip install -e '.[harmony]'
```

```python
from getpass import getpass
from jev_phone import AndroidClicker

with AndroidClicker(
    serial="YOUR_DEVICE_SERIAL",
    api_key=getpass("OpenRouter Key: "),
    provider="openrouter",  # 官方通道使用 openai
) as phone:
    report = phone.run("打开练习设置；选择困难；点击开始挑战")
    print(report["results"])
```

iOS 使用 `IOSClicker(wda_url=..., api_key=...)`，鸿蒙使用 `HarmonyClicker(serial=..., api_key=...)`。外部接入不需要运行网页或数据库。支持 OpenRouter 多模态 Decisions 与 OpenAI 官方 Decisions；两种通道使用各自凭证。

![官网独立组件接入](docs/media/modules/integration.png)

[SDK 接入指南](docs/接入指南.md) · [三端设备准备](docs/三端设备准备.md) · [调用示例](examples/click.py) · [多设备并行](examples/parallel.py)

## Demo 与交付范围

Demo 展示只读实时镜像、步骤日志、模型实际收到的编号图，以及选择、坐标与分段耗时。网页体验端目前为安卓；SDK 三端调用不依赖该界面。

![Demo完整界面](docs/media/site-demo.png)

安装 Demo 依赖后启动：

```sh
.venv/bin/pip install -e '.[demo]'
.venv/bin/jev-phone-demo
```

准备 `adb`、`scrcpy`、`ffmpeg`，打开 `http://127.0.0.1:8765/`。Key 在页面中输入，刷新清除。SDK 密钥由调用方提供，截图与执行记录作为本地产物保存。

![官网能力与实践说明](docs/media/modules/practice.png)

当前交付单步与多步点击。规划、缓存、业务断言、应用启动和设备调度由外部系统承接；输入、滚动、长按等动作不属于当前交付范围。设备授权、WDA签名和虚拟机生命周期由使用者准备。

[验证概览](docs/验证概览.md) · [MIT 许可证](LICENSE) · [来源说明](NOTICE.md) · [完整官网技术原图](docs/media/site-guide.png)

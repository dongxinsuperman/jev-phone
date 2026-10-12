# Jev Phone

Jev Phone 是面向 Android、iOS、HarmonyOS 的独立 Python 点击 SDK。它将当前系统层级与截图生成带编号的候选区域，由多模态模型选择编号，再通过设备驱动完成点击。支持单步调用，也支持按标点或换行拆分目标、逐步执行。

## 执行演示

### 选择难度并开始挑战

下面使用真实安卓手机，连续完成三个操作：打开练习设置、选择最右侧橙色困难卡片、开始挑战。最终进入困难题目。

![真实安卓手机连续点击演示](docs/media/demo-hard-challenge.gif)

三个步骤的模型请求往返分别为 **1944.83ms、1025.65ms、765.28ms**。整段执行 **6.57 秒**，包含截图、候选生成、模型请求、点击及步骤间图片对比；视频原速播放，右上角秒表显示累计执行时间。

[观看视频](docs/media/demo-hard-challenge.mp4) · [计时记录](docs/media/demo-hard-challenge.json)

### 浏览章节并打开练习设置

依次点击“集合间的基本关系”和“集合的基本运算”，再点击右上方黄色铅笔打开练习设置。每一步只向模型传入当前操作目标。

![章节切换与练习设置](docs/media/demo-section-switch.gif)

三个步骤的模型请求往返分别为 **827.78ms、693.05ms、1999.53ms**。上述两段演示的每步模型请求均低于2秒；这个数值不包含设备采集、点击和步骤衔接时间。[观看视频](docs/media/demo-section-switch.mp4) · [计时记录](docs/media/demo-section-switch.json)

## 演示界面

Demo 使用同一套 SDK，展示手机实时镜像、逐步执行日志，以及实际发送给模型的编号图。每步可以查看选中区域、点击坐标和分段耗时；网页演示目前使用安卓设备。

![点击演示](docs/media/site-demo.png)

## 技术与接入说明

候选编号绑定当前画面的区域，模型在有限候选中选择，SDK 负责坐标映射与平台点击。多步执行时，通过图片对比衔接下一步并复用末帧。三端共用定位流程，分别适配 UiAutomator2、WDA 与 UITest；SDK 不依赖演示网页或 AI Phone 框架。

![技术与接入说明](docs/media/site-guide.png)

## 安装与调用

Python 3.10+。从仓库安装，尚未发布到 PyPI。

```sh
git clone https://github.com/dongxinsuperman/jev-phone.git
cd jev-phone
python3 -m venv .venv
.venv/bin/pip install -e '.[android]'
```

```python
from getpass import getpass
from jev_phone import AndroidClicker

with AndroidClicker(
    serial="YOUR_DEVICE_SERIAL",
    api_key=getpass("OpenRouter Key: "),
) as phone:
    report = phone.run("打开练习设置；选择困难；点击开始挑战")
    print(report["results"])
```

Android、iOS、HarmonyOS · 真机／虚拟机。Demo 与独立 SDK 使用同一执行流程。

[SDK 接入指南](docs/接入指南.md) · [三端设备准备](docs/三端设备准备.md) · [验证概览](docs/验证概览.md) · [调用示例](examples/click.py) · [多设备并行](examples/parallel.py)

[MIT 许可证](LICENSE) · [来源说明](NOTICE.md)

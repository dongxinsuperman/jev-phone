<h1 align="center">Jev Phone</h1>
<p align="center"><strong>毫秒级本地处理的三端多模态点击 SDK</strong></p>
<p align="center">Android · iOS · HarmonyOS<br>真机与虚拟机 · 单步与连续点击 · Python · MIT</p>
<p align="center"><a href="README.md">中文</a> · <a href="README.en.md">English</a></p>

Jev Phone 将 Jev 多模态决策接到三端设备上，为已有 Agent、测试平台和脚本提供可独立调用的手机点击能力。**调用方给出点击目标，SDK 完成当前画面的定位和执行。**

它承接从“知道要操作什么”到“实际点到设备上”的这一段。你可以继续使用自己的任务规划、缓存和业务判断，不需要引入完整 AI Phone 框架。

<!-- Two demonstration GIFs belong here only after every complete step is <=1700ms. -->

[![Demo首页完整高清图](docs/media/demo-home-hd.jpg)](docs/media/demo-home-hd.jpg)

![多模态决策驱动的三端视觉交互通道](docs/media/readme/overview.zh.png)

## 性能

已有安卓实验中，本地候选处理、画框与编码耗时 **15–50ms**；非模型整轮中位为 **620ms**，同一导航样本9轮范围为 **493–729ms**。这些数据不包含模型请求、初始化与页面稳定。

每一步整体耗时还包括设备采集、候选处理、模型往返、点击和该步后续衔接。[完整分段记录](docs/演示耗时明细.md)分别列出这些时间。

![毫秒级通道处理与分段计时](docs/media/readme/timing.zh.png)

![视觉目标定位与设备动作绑定](docs/media/readme/binding.zh.png)

## 为什么结合系统树与截图

系统树能提供控件边界和属性，但图标可能没有文字，节点名称也可能与画面不一致；截图能呈现图标和文字，却还需要确定可执行的位置。把两者结合后，模型依据画面理解目标，组件依据区域边界完成点击绑定。

![几何约束与视觉语义融合](docs/media/readme/geometry.zh.png)

![三端视觉定位与执行验证](docs/media/readme/platforms.zh.png)

## 独立组件接入

把手机点击能力接到你已有的程序中：准备好设备服务和模型 Key，创建目标平台的 Clicker。单个点击目标调用 `click(target)`，一组有序目标调用 `run(text)`；组件返回选中区域、坐标、驱动状态和分段耗时，让你的程序继续处理后续流程。

接入不需要运行 Demo 网页或数据库。安卓、iOS、鸿蒙分别使用 `AndroidClicker`、`IOSClicker`、`HarmonyClicker`，模型通道配置和异常处理见接入指南。

[SDK接入指南](docs/接入指南.md) · [三端设备准备](docs/三端设备准备.md) · [调用示例](examples/click.py) · [多设备并行](examples/parallel.py)

## 当前能力与后续承接

当前支持 Android、iOS、HarmonyOS 真机与虚拟机上的单步和连续点击，完成画面采集、候选生成、模型选择、点击执行，并返回结果与计时。

后续可扩展输入、滚动、长按等动作。任务规划、业务断言、应用启动和设备调度由现有系统承接，可以围绕点击组件继续集成。

## 接入代码

Python 3.10+。从仓库安装：

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
    provider="openrouter",
) as phone:
    report = phone.run("打开默认难度设置；选择中等难度；保存修改")
    print(report["results"])
```

[SDK接入指南](docs/接入指南.md) · [三端设备准备](docs/三端设备准备.md) · [验证概览](docs/验证概览.md) · [完整计时记录](docs/演示耗时明细.md) · [页面源码](docs/readme-site/manual.zh.html) · [MIT](LICENSE)

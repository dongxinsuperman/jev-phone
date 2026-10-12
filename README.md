# Jev Phone

**描述目标，让手机点击。**

![真实安卓手机连续点击演示](docs/media/demo-hard-challenge.gif)

打开练习设置 → 选择困难 → 开始挑战。模型识别分别 **1.94s / 1.03s / 0.77s**；秒表连续计时，原速播放。

[观看视频](docs/media/demo-hard-challenge.mp4) · [计时记录](docs/media/demo-hard-challenge.json)

![点击演示](docs/media/site-demo.png)

![章节切换与练习设置](docs/media/demo-section-switch.gif)

切换两个章节 → 打开练习设置。模型识别分别 **0.83s / 0.69s / 2.00s**（原始值1999.53ms）。[观看视频](docs/media/demo-section-switch.mp4)

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

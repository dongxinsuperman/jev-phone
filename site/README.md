# 官网

独立静态官网，复用Demo视觉和真实原速录制。不连接设备、不填写Key、不调用模型。

本地预览：`python3 -m http.server 8766 --directory site`，打开`http://127.0.0.1:8766/`。

`demo.css`与技术说明初始复制自Demo；`site.css`、`site.js`和媒体独立维护。计时来自现有达标录制的JSON。更新官网不会影响SDK或本地Demo。

GitHub Pages工作流只部署site目录。

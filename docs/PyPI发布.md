# PyPI 发布维护

包名称：`jev-phone`。版本由`pyproject.toml`管理，项目介绍由`README.md`生成；生成文件为`README.pypi.md`，将本地图片和文档链接转换为公开URL。

## 账号配置

登录PyPI，验证邮箱并启用双因素认证。在 [Publishing](https://pypi.org/manage/account/publishing/) 页面添加 GitHub pending publisher：

| 字段 | 值 |
|---|---|
| PyPI Project Name | `jev-phone` |
| Owner | `dongxinsuperman` |
| Repository name | `jev-phone` |
| Workflow name | `publish-pypi.yml` |
| Environment name | `pypi` |

GitHub工作流使用OIDC可信发布，无需在仓库配置PyPI密码或Token。首次成功上传后，pending publisher会创建项目并成为该项目的publisher。pending publisher本身不占用项目名称。

官方说明：[创建项目的可信发布](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)。

## 构建与检查

在仓库根目录执行：

```sh
python scripts/build_pypi_readme.py
python -m pip install build twine
python -m build --outdir pypi-dist
python -m twine check --strict pypi-dist/*
```

发布前重新生成介绍页并提交源码。保持已发布版本不可变；下一次SDK更新提升版本号后重新构建。

## GitHub Actions

工作流为`.github/workflows/publish-pypi.yml`，仅手动触发：

- `publish=false`：运行SDK单元测试，构建wheel和sdist，检查介绍页与格式，验证独立wheel安装，保存构建产物，不上传PyPI。
- `publish=true`且运行分支为main：上述检查通过后，使用`pypi`环境身份上传同一批构建产物。

从 [Actions](https://github.com/dongxinsuperman/jev-phone/actions/workflows/publish-pypi.yml) 的Run workflow入口选择模式。仓库代码提交或GitHub Release创建不会自动上传PyPI。

## 发布读回

上传成功后，确认PyPI项目页版本、介绍和下载文件，再在新虚拟环境中执行`python -m pip install 'jev-phone[android]==0.1.1'`与版本读回。仅在这些检查完成后，更新README与升级说明中的PyPI安装方式。

官方说明：[使用可信发布](https://docs.pypi.org/trusted-publishers/using-a-publisher/)。

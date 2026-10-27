# AI News Factory — Muse → Windows V1

一个面向中文 AI 资讯项目的 **Windows 本地验证版**。用 Muse 输出的 JSON，完成校验、SQLite 去重存档、人工审核、结构化草稿和 FFmpeg 视频测试。

> **当前不是完整的无人值守生产系统。** 尚未接入 Muse/Dropbox 自动同步、在线模型 API、商业 TTS、公众号/视频号自动发布。未经人工复核的内容禁止发布。

## Windows 安装

1. 安装 [Python 3.10+](https://www.python.org/downloads/windows/)（安装时勾选添加至 PATH）。
2. 如果要渲染视频，再安装 [FFmpeg](https://ffmpeg.org/download.html)，确保 `ffmpeg -version` 可运行。
3. 在仓库页面点 **Code → Download ZIP**，解压至如 `D:\AI-News-Factory`。
4. 在解压目录打开 PowerShell，按顺序运行：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe news_factory.py check samples\example.json
.\.venv\Scripts\python.exe news_factory.py import samples\example.json
.\.venv\Scripts\python.exe news_factory.py report --date 2026-10-27
.\.venv\Scripts\python.exe news_factory.py render --date 2026-10-27 --demo
```

渲染完成后，双击 `output\2026-10-27\review.html`，打开审核页；测试视频在 `output\2026-10-27\demo_video\DEMO_NOT_FOR_PUBLICATION.mp4`。

## 导入真实 Muse 新闻

将 Muse 下载的 `2026-10-27.json` 放入 `inbox` 目录（若不存在就创建），然后执行：

```powershell
.\.venv\Scripts\python.exe news_factory.py check inbox\2026-10-27.json
.\.venv\Scripts\python.exe news_factory.py import inbox\2026-10-27.json
.\.venv\Scripts\python.exe news_factory.py report --date 2026-10-27
```

兼容 Muse 旧格式 `date/items/verification: pending` 和新格式 `report_date/news/verification_status: needs_review`。

每条新闻**默认进入人工待审核**，即便 Muse 标记 verified。核实来源后才可手动执行：

```powershell
.\.venv\Scripts\python.exe news_factory.py approve 20261027-EXAMPLE --checked --note "已人工核对"
.\.venv\Scripts\python.exe news_factory.py draft --date 2026-10-27
```

对于 Muse 标记 pending / unverified 的条目，即使想批准，也必须额外加 `--override-pending` 并先取得独立证据。

## 功能和限制

- ✅ 校验 JSON、URL、必填字段；不访问不可信新闻 URL
- ✅ SQLite 保存、重复导入不增加新闻、内容变动自动撤销旧审批
- ✅ 只读 HTML 审核页面；CLI 人工批准/驳回
- ✅ 仅使用获批条目生成 **结构化草稿**，不是高质量模型原创
- ✅ Pillow + FFmpeg 合成竖屏 **无配音演示**，带禁止发布水印
- ❌ 尚无实时来源事实验证、自动化 TTS、音画同步或账号发布权限
- ❌ 不上传账号 Cookies、API 密钥、个人新闻档案

## 安全说明

- 仓库若为 **Public**，任何人可阅读源码。请只在本机 `inbox/`、`data/`、`output/` 保存私人新闻和生成成果。
- `.env`、数据库、新闻收件箱和输出目录已写入 `.gitignore`。
- 视频内容由未经验证的示例数据生成时必须只做测试，不得对外发布。

开发目标：先验证 Muse JSON → Windows → SQLite → 审核页 → 演示视频链路，然后再接 Dropbox 及高质量写稿/TTS。

# AniFlow

绝区零 (Zenless Zone Zero) + 终末地 (Endfield) 自动化调度启动器。

整合 [OneDragon](https://one-dragon.com/zzz/zh/feat_one_dragon/onedragon.html)（绝区零）和 [MaaEnd](https://github.com/MaaXYZ/MaaEnd)（终末地），提供统一的可视化管理界面和一键运行管道。

## 功能

- **一键管道**：按配置顺序依次执行多个自动化工具，完成后可自动关闭游戏或关机
- **工具管理**：扫描本地安装或自动下载 OneDragon、MaaEnd
- **独立控制**：每个工具可单独「打开」/「关闭」
- **实时状态**：进程状态 + 日志输出实时推送

![主界面](screenshots/main.png)

## 下载

从 [Releases](https://github.com/ace-yong/AniFlow/releases) 下载最新版压缩包，解压后双击 `AniFlow.exe` 运行。
首次运行会弹出用户账户控制(UAC)提示，点「是」以管理员权限启动。

数据文件自动在 exe 同级生成：

```
AniFlow.exe
└── resources/
    ├── gui_server.exe      ← 后端服务器（已编译，无需 Python）
    └── renderer/            ← Web 前端界面
```

## 使用

### 配置工具路径

| 方式 | 说明 |
|------|------|
| 自动扫描 | 选择盘符，点击检测，自动查找 onedragon / MaaEnd 目录 |
| 手动输入 | 直接填写路径 |
| 下载安装 | 自动从 GitHub / Gitee 拉取并安装 |

### 管道执行

点击 **▶ 一键运行** 按配置顺序依次执行。支持执行超时、失败重试、切换延迟。

### 启动/停止

每张工具卡片可单独「打开」/「关闭」，状态实时更新。

## 打包

```bash
cd electron
npm install
npm run dist
```

输出在 `electron/aniflow-*/` 目录。

## 技术栈

- **前端**：Electron + 原生 HTML/CSS/JS
- **后端**：Python HTTP 服务器（PyInstaller 编译为单 exe）
- **通信**：REST API + SSE 实时推送
- **进程管理**：subprocess.Popen / ShellExecuteW + tasklist 轮询

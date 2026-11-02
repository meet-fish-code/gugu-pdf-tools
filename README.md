# 咕咕PDF工具箱（Gugu PDF Tools）

**一款基于 Tauri 2 + Vue 3 + Python 开发的 Windows 桌面 PDF 文件处理工具箱。**

咕咕PDF工具箱是一款面向日常办公场景的本地文件处理软件，集成 PDF 页面处理、文件转换、压缩、安全与权限管理等常用功能。

软件采用本地处理模式，文件无需上传至远程服务器，减少文件传输环节，让文档处理更加便捷、安全。

## 功能介绍

### PDF 页面处理

- **PDF 合并**：将多个 PDF 文件合并为一个文件。
- **PDF 拆分**：支持拆分 PDF 页面及指定页面范围。
- **PDF 去水印**：处理 PDF 文档中的水印内容。
- **PDF 加水印**：支持文字水印和图片水印，可设置位置、透明度、旋转角度等参数。

### 文件处理

- **PDF 压缩**：压缩 PDF 文件，减少文档体积。
- **Word 转 PDF**：将 Word 文档转换为 PDF 格式。
- **图片转 PDF**：将图片文件转换为 PDF 文档。
- **PDF 转图片**：将 PDF 页面导出为图片。

### 安全与权限

- **PDF 添加密码**：支持设置文档打开密码和权限密码。
- **PDF 解密**：移除 PDF 文档的权限限制，适用于拥有相应权限密码的文档。
- **权限管理**：支持配置打印、复制、修改等文档操作权限。

## 技术栈

| 技术 | 用途 |
|---|---|
| Tauri 2 | Windows 桌面应用框架 |
| Vue 3 | 前端界面开发 |
| TypeScript | 前端类型系统 |
| Vite | 前端构建工具 |
| Rust | 桌面应用后端及系统交互 |
| Python | PDF 文件处理与转换 |
| PyInstaller | Python 程序打包 |

## 项目特点

- **本地文件处理**：文件处理过程在本地完成，无需上传至远程服务器。
- **功能集成**：整合多种常用 PDF 文件处理功能，减少不同工具之间的切换。
- **桌面应用体验**：基于 Tauri 构建，提供轻量化的 Windows 桌面使用体验。
- **前后端分离**：Vue 负责界面交互，Rust 负责桌面能力与外部程序调用，Python 负责具体文件处理。
- **模块化设计**：各项文件处理功能相对独立，便于后续维护和扩展。

## 项目结构

```text
gugu-pdf-tools/
├── public/                 # 静态资源
├── src/                    # Vue 前端代码
│   ├── App.vue
│   └── main.ts
├── src-tauri/              # Tauri / Rust 后端
│   ├── binaries/            # PDF 处理程序
│   ├── icons/               # 应用图标
│   ├── src/
│   │   ├── lib.rs
│   │   └── main.rs
│   ├── Cargo.toml
│   └── tauri.conf.json
├── python/                 # Python 文件处理源码
├── *.spec                  # PyInstaller 打包配置
├── package.json
├── pnpm-lock.yaml
└── README.md
```

## 开发环境

开始开发前，请准备以下环境：

- Windows 10 / Windows 11
- Node.js
- pnpm
- Rust
- Tauri 2 开发环境

## 本地开发

克隆项目：

```bash
git clone https://github.com/meet-fish-code/gugu-pdf-tools.git
cd gugu-pdf-tools
```

安装前端依赖：

```bash
pnpm install
```

启动开发环境：

```bash
pnpm tauri dev
```

构建前端：

```bash
pnpm build
```

构建 Windows 桌面安装包：

```bash
pnpm tauri build
```

## 关于项目

**项目名称：** 咕咕PDF工具箱

**英文名称：** Gugu PDF Tools

**开发框架：** Tauri 2 + Vue 3 + TypeScript + Rust + Python

**应用平台：** Windows

本项目持续迭代开发，致力于提供简单、实用、高效的本地 PDF 文件处理体验。

## 开源许可

本项目采用 GNU General Public License v3.0（GPL-3.0）开源许可证。

你可以在遵守许可证条款的前提下自由使用、学习、修改和分发本项目。

完整许可证内容请参阅项目根目录下的 [LICENSE](./LICENSE) 文件。

## 开源致谢

本项目的开发过程中使用了以下开源技术及项目，感谢相关开发者和社区的贡献：

- [Tauri](https://tauri.app/)
- [Vue.js](https://vuejs.org/)
- [TypeScript](https://www.typescriptlang.org/)
- [Vite](https://vite.dev/)
- [Rust](https://www.rust-lang.org/)
- [Python](https://www.python.org/)
- [PyInstaller](https://pyinstaller.org/)

---

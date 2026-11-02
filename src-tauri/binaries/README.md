# PDF 转图片工具 - 本地构建说明

本目录用于存放咕咕 PDF 工具箱所需的 Python 打包程序。

由于 `pdf_to_images.exe` 文件较大，仓库不直接提供该文件。使用者可以通过项目中的 Python 源码自行构建。

## 1. 环境准备

确保已经安装 Python 和 PyInstaller。

安装 PyInstaller：

```bash
pip install pyinstaller
```

如果项目使用了其他 Python 依赖，请根据实际情况安装对应依赖。

## 2. 执行打包

在项目根目录（包含 `pdf_to_images.spec` 的目录）打开终端，执行：

```bash
pyinstaller --clean --noconfirm pdf_to_images.spec
```

## 3. 放置打包文件

打包完成后，将生成的 `pdf_to_images.exe` 复制到当前目录：

```text
src-tauri/binaries/
```

最终文件路径应为：

```text
src-tauri/binaries/pdf_to_images.exe
```

## 4. 注意事项

- `pdf_to_images.exe` 不纳入 Git 仓库版本管理。
- 本程序由项目使用者根据 Python 源码自行构建。
- 构建完成后，请确保 EXE 文件名称为 `pdf_to_images.exe`。
- 请勿修改程序文件名，否则可能影响 Tauri 对外部程序的调用。
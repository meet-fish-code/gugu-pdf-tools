
use serde::Serialize;
use serde_json::Value;
use std::io::Write;
use std::os::windows::process::CommandExt;
use std::path::PathBuf;
use std::process::{Command, Stdio};
use tauri::Manager;

// #region 常量配置

/// Windows 下启动外部程序时不显示命令行窗口。
const CREATE_NO_WINDOW: u32 = 0x08000000;

// #endregion

// #region 外部程序调用

/// 获取外部 EXE 文件路径。
///
/// 优先使用应用打包后的资源目录，开发环境下使用项目目录。
fn get_exe_path(app: &tauri::AppHandle, exe_name: &str) -> Result<PathBuf, String> {
    let resource_dir = app
        .path()
        .resource_dir()
        .map_err(|e| format!("无法获取应用资源目录：{}", e))?;

    let resource_path = resource_dir.join("binaries").join(exe_name);

    if resource_path.is_file() {
        return Ok(resource_path);
    }

    let dev_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("binaries")
        .join(exe_name);

    if dev_path.is_file() {
        return Ok(dev_path);
    }

    Err(format!(
        "找不到程序 {}，已检查以下路径：\n{}\n{}",
        exe_name,
        resource_path.display(),
        dev_path.display()
    ))
}

/// 通过 JSON 标准输入调用外部 EXE。
///
/// Python 程序从 stdin 读取参数，并通过 stdout 返回 JSON 结果。
fn run_json_exe(
    app: &tauri::AppHandle,
    exe_name: &str,
    params: Value,
    task_name: &str,
) -> Result<String, String> {
    let exe_path = get_exe_path(app, exe_name)?;

    let json_input =
        serde_json::to_vec(&params).map_err(|e| format!("{}参数序列化失败：{}", task_name, e))?;

    let mut child = Command::new(&exe_path)
        .creation_flags(CREATE_NO_WINDOW)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("无法启动{}程序：{}", task_name, e))?;

    {
        let stdin = child
            .stdin
            .as_mut()
            .ok_or_else(|| format!("无法打开{}程序的标准输入", task_name))?;

        stdin
            .write_all(&json_input)
            .map_err(|e| format!("传递{}参数失败：{}", task_name, e))?;
    }

    let output = child
        .wait_with_output()
        .map_err(|e| format!("等待{}程序结束失败：{}", task_name, e))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();

    if !output.status.success() {
        return Err(if !stderr.trim().is_empty() {
            format!("{}程序执行失败：{}", task_name, stderr)
        } else if !stdout.trim().is_empty() {
            format!("{}程序执行失败：{}", task_name, stdout)
        } else {
            format!("{}程序执行失败，退出状态：{}", task_name, output.status)
        });
    }

    if stdout.trim().is_empty() {
        return Err(format!("{}程序没有返回处理结果", task_name));
    }

    Ok(stdout)
}

/// 执行阻塞任务，避免外部程序调用占用异步运行时线程。
async fn run_blocking<F, T>(task_name: &str, task: F) -> Result<T, String>
where
    F: FnOnce() -> Result<T, String> + Send + 'static,
    T: Send + 'static,
{
    tauri::async_runtime::spawn_blocking(task)
        .await
        .map_err(|e| format!("{}任务执行异常：{}", task_name, e))?
}

// #endregion

// #region 系统字体

#[derive(Serialize)]
struct SystemFont {
    name: String,
    path: String,
    index: u32,
}

// #endregion

// #region PDF 密码处理

/// 批量解密 PDF。
///
/// 参数顺序：输出目录在前，输入文件在后。
#[tauri::command]
async fn unlock_pdfs(
    app: tauri::AppHandle,
    files: Vec<String>,
    output_folder: String,
) -> Result<String, String> {
    run_blocking("PDF 解密", move || {
        if files.is_empty() {
            return Err("请至少选择一个 PDF 文件".to_string());
        }

        let exe_path = get_exe_path(&app, "pdf_unlock.exe")?;

        let output = Command::new(&exe_path)
            .creation_flags(CREATE_NO_WINDOW)
            .arg(&output_folder)
            .args(&files)
            .output()
            .map_err(|e| format!("无法启动 PDF 解密程序：{}", e))?;

        let stdout = String::from_utf8_lossy(&output.stdout).to_string();
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();

        if !output.status.success() {
            return Err(if stderr.trim().is_empty() {
                format!("PDF 解密程序执行失败：{}", stdout)
            } else {
                format!("PDF 解密程序执行失败：{}", stderr)
            });
        }

        if stdout.trim().is_empty() {
            return Err("PDF 解密程序没有返回处理结果".to_string());
        }

        Ok(stdout)
    })
    .await
}

/// 给 PDF 添加密码。
///
/// 密码通过标准输入传递，不放入命令行参数。
#[tauri::command]
async fn protect_pdf(
    app: tauri::AppHandle,
    params: Value,
) -> Result<String, String> {
    run_blocking("PDF 加密", move || {
        let exe_path = get_exe_path(&app, "pdf_password.exe")?;

        let json_input =
            serde_json::to_vec(&params).map_err(|e| format!("加密参数序列化失败：{}", e))?;

        let mut child = Command::new(&exe_path)
            .creation_flags(CREATE_NO_WINDOW)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|e| format!("无法启动 PDF 加密程序：{}", e))?;

        {
            let stdin = child
                .stdin
                .as_mut()
                .ok_or_else(|| "无法打开 PDF 加密程序的标准输入".to_string())?;

            stdin
                .write_all(&json_input)
                .map_err(|e| format!("传递加密参数失败：{}", e))?;
        }

        // 关闭 stdin 后，子进程才能继续读取完参数并退出。
        let output = child
            .wait_with_output()
            .map_err(|e| format!("等待 PDF 加密程序结束失败：{}", e))?;

        let stdout = String::from_utf8_lossy(&output.stdout).to_string();
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();

        if !output.status.success() {
            return Err(if stderr.trim().is_empty() {
                format!("PDF 加密程序执行失败：{}", stdout)
            } else {
                format!("PDF 加密程序执行失败：{}", stderr)
            });
        }

        if stdout.trim().is_empty() {
            return Err(if stderr.trim().is_empty() {
                "PDF 加密程序没有返回处理结果".to_string()
            } else {
                format!("PDF 加密程序没有返回结果：{}", stderr)
            });
        }

        Ok(stdout)
    })
    .await
}

// #endregion

// #region PDF 压缩

/// 批量压缩 PDF。
///
/// 参数顺序：输出目录在前，输入文件在后。
#[tauri::command]
async fn compress_pdfs(
    app: tauri::AppHandle,
    files: Vec<String>,
    output_folder: String,
) -> Result<String, String> {
    run_blocking("PDF 压缩", move || {
        use std::path::Path;

        if files.is_empty() {
            return Err("请至少选择一个 PDF 文件".to_string());
        }

        for file in &files {
            let path = Path::new(file);

            if !path.is_file() {
                return Err(format!(
                    "输入文件不存在或不是文件：{}\n当前工作目录：{:?}",
                    file,
                    std::env::current_dir().ok()
                ));
            }
        }

        let output_path = Path::new(&output_folder);

        if !output_path.is_dir() {
            return Err(format!("输出目录不存在：{}", output_folder));
        }

        let exe_path = get_exe_path(&app, "pdf_compress.exe")?;

        eprintln!("压缩程序路径：{}", exe_path.display());
        eprintln!("输入文件：{:#?}", files);
        eprintln!("输出目录：{}", output_folder);

        let output = Command::new(&exe_path)
            .creation_flags(CREATE_NO_WINDOW)
            .arg(&output_folder)
            .args(&files)
            .output()
            .map_err(|e| format!("无法启动 PDF 压缩程序：{}", e))?;

        let stdout = String::from_utf8_lossy(&output.stdout).to_string();
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();

        if !output.status.success() {
            return Err(format!(
                "PDF 压缩程序执行失败。\n程序：{}\n退出状态：{}\n标准输出：{}\n错误输出：{}",
                exe_path.display(),
                output.status,
                stdout,
                stderr
            ));
        }

        if stdout.trim().is_empty() {
            return Err(format!(
                "PDF 压缩程序没有返回处理结果。\n标准错误：{}",
                stderr
            ));
        }

        Ok(stdout)
    })
    .await
}

// #endregion

// #region PDF 水印处理

/// 给 PDF 添加文字或图片水印。
#[tauri::command]
async fn add_pdf_watermark(
    app: tauri::AppHandle,
    params: Value,
) -> Result<String, String> {
    run_blocking("PDF 水印", move || {
        run_json_exe(&app, "pdf_watermark.exe", params, "PDF 水印")
    })
    .await
}

/// 移除 PDF 中的水印。
#[tauri::command]
async fn remove_pdf_watermark(
    app: tauri::AppHandle,
    params: Value,
) -> Result<String, String> {
    run_blocking("PDF 去水印", move || {
        run_json_exe(
            &app,
            "pdf_remove_watermark.exe",
            params,
            "PDF 去水印",
        )
    })
    .await
}

// #endregion

// #region Word 转 PDF

/// 批量转换 Word 文档。
///
/// 参数顺序：输入文件在前，输出目录在后。
#[tauri::command]
async fn word_to_pdf(
    app: tauri::AppHandle,
    files: Vec<String>,
    output_folder: String,
) -> Result<String, String> {
    run_blocking("Word 转 PDF", move || {
        if files.is_empty() {
            return Err("请至少选择一个 Word 文件".to_string());
        }

        let exe_path = get_exe_path(&app, "word_to_pdf.exe")?;

        let output = Command::new(&exe_path)
            .creation_flags(CREATE_NO_WINDOW)
            .args(&files)
            .arg(&output_folder)
            .output()
            .map_err(|e| format!("无法启动 Word 转 PDF 程序：{}", e))?;

        let stdout = String::from_utf8_lossy(&output.stdout).to_string();
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();

        if !output.status.success() {
            return Err(if !stderr.trim().is_empty() {
                format!("Word 转 PDF 程序执行失败：{}", stderr)
            } else if !stdout.trim().is_empty() {
                format!("Word 转 PDF 程序执行失败：{}", stdout)
            } else {
                "Word 转 PDF 程序执行失败，请检查转换程序和依赖。".to_string()
            });
        }

        if stdout.trim().is_empty() {
            return Err(if stderr.trim().is_empty() {
                "Word 转 PDF 程序没有返回处理结果".to_string()
            } else {
                format!("Word 转 PDF 程序没有返回结果：{}", stderr)
            });
        }

        Ok(stdout)
    })
    .await
}

// #endregion

// #region PDF 与图片格式转换

/// 将 PDF 页面转换为图片。
#[tauri::command]
async fn pdf_to_images(
    app: tauri::AppHandle,
    params: Value,
) -> Result<String, String> {
    run_blocking("PDF 转图片", move || {
        run_json_exe(&app, "pdf_to_images.exe", params, "PDF 转图片")
    })
    .await
}

/// 将图片转换为 PDF。
#[tauri::command]
async fn images_to_pdf(
    app: tauri::AppHandle,
    params: Value,
) -> Result<String, String> {
    run_blocking("图片转 PDF", move || {
        run_json_exe(&app, "images_to_pdf.exe", params, "图片转 PDF")
    })
    .await
}

// #endregion

// #region PDF 页面处理

/// 合并多个 PDF 文件。
#[tauri::command]
async fn pdf_merge(
    app: tauri::AppHandle,
    params: Value,
) -> Result<String, String> {
    run_blocking("PDF 合并", move || {
        run_json_exe(&app, "pdf_merge.exe", params, "PDF 合并")
    })
    .await
}

/// 拆分 PDF，支持逐页拆分和指定页面范围。
#[tauri::command]
async fn pdf_split(
    app: tauri::AppHandle,
    params: Value,
) -> Result<String, String> {
    run_blocking("PDF 拆分", move || {
        run_json_exe(&app, "pdf_split.exe", params, "PDF 拆分")
    })
    .await
}

// #endregion

// #region 系统字体扫描

/// 扫描 Windows 系统字体。
///
/// 支持系统字体目录、当前用户字体目录，以及 TTF、OTF、TTC 字体文件。
/// TTC 文件会分别读取其中的字体面。
#[tauri::command]
async fn list_system_fonts() -> Result<Vec<SystemFont>, String> {
    run_blocking("字体扫描", || {
        use std::collections::HashSet;

        let mut directories = Vec::new();

        // Windows 系统字体目录。
        if let Ok(windir) = std::env::var("WINDIR") {
            directories.push(PathBuf::from(windir).join("Fonts"));
        }

        // 当前用户安装的字体目录。
        if let Ok(local) = std::env::var("LOCALAPPDATA") {
            directories.push(
                PathBuf::from(local)
                    .join("Microsoft")
                    .join("Windows")
                    .join("Fonts"),
            );
        }

        let mut fonts = Vec::new();
        let mut seen = HashSet::new();

        for directory in directories {
            if !directory.is_dir() {
                continue;
            }

            let entries = match std::fs::read_dir(&directory) {
                Ok(entries) => entries,
                Err(error) => {
                    eprintln!("无法读取字体目录 {}：{}", directory.display(), error);
                    continue;
                }
            };

            for entry in entries.flatten() {
                let path = entry.path();

                if !path.is_file() {
                    continue;
                }

                let extension = path
                    .extension()
                    .and_then(|value| value.to_str())
                    .unwrap_or("")
                    .to_lowercase();

                if !["ttf", "otf", "ttc"].contains(&extension.as_str()) {
                    continue;
                }

                let data = match std::fs::read(&path) {
                    Ok(data) => data,
                    Err(error) => {
                        eprintln!("无法读取字体文件 {}：{}", path.display(), error);
                        continue;
                    }
                };

                // TTC 文件可能包含多个字体面。
                let face_count = ttf_parser::fonts_in_collection(&data).unwrap_or(1);

                for index in 0..face_count {
                    let face = match ttf_parser::Face::parse(&data, index) {
                        Ok(face) => face,
                        Err(_) => continue,
                    };

                    // 优先使用字体族名称，其次使用完整名称和 PostScript 名称。
                    let name = face
                        .names()
                        .into_iter()
                        .filter(|record| record.is_unicode())
                        .find(|record| record.name_id == 1)
                        .and_then(|record| record.to_string())
                        .or_else(|| {
                            face.names()
                                .into_iter()
                                .filter(|record| record.is_unicode())
                                .find(|record| record.name_id == 4)
                                .and_then(|record| record.to_string())
                        })
                        .or_else(|| {
                            face.names()
                                .into_iter()
                                .filter(|record| record.is_unicode())
                                .find(|record| record.name_id == 6)
                                .and_then(|record| record.to_string())
                        });

                    let Some(name) = name else {
                        continue;
                    };

                    let font_path = path.to_string_lossy().to_string();

                    // 同一路径下的不同字体面需要分别保留。
                    let key = (font_path.to_lowercase(), index);

                    if !seen.insert(key) {
                        continue;
                    }

                    fonts.push(SystemFont {
                        name,
                        path: font_path,
                        index,
                    });
                }
            }
        }

        // 按名称排序，方便前端选择。
        fonts.sort_by(|a, b| {
            a.name
                .to_lowercase()
                .cmp(&b.name.to_lowercase())
                .then(a.path.cmp(&b.path))
                .then(a.index.cmp(&b.index))
        });

        eprintln!("系统字体扫描完成，共找到 {} 个字体面", fonts.len());

        Ok(fonts)
    })
    .await
}

// #endregion

// #region 测试命令

/// 测试前后端通信。
#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

// #endregion

// #region Tauri 应用入口

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        // 单实例插件放在其他插件之前初始化。
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.unminimize();
                let _ = window.set_focus();
            }
        }))
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            greet,
            unlock_pdfs,
            protect_pdf,
            compress_pdfs,
            add_pdf_watermark,
            remove_pdf_watermark,
            word_to_pdf,
            pdf_to_images,
            images_to_pdf,
            pdf_merge,
            pdf_split,
            list_system_fonts
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

// #endregion
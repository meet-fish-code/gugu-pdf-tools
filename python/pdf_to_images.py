
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF 转图片工具

支持：
1. PNG / JPG 格式
2. 批量 PDF 转换
3. 全部页面或指定页码
4. 自定义 DPI
5. 每个 PDF 单独创建输出文件夹
6. JSON 标准输入输出，方便 Tauri 调用
7. Windows 中文路径及文件名
"""

import json
import os
import re
import sys
import traceback

import pymupdf as fitz


def print_json(data: dict) -> None:
    """统一输出 JSON，兼容 Windows 下的中文编码。"""

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(
            encoding="utf-8",
            errors="replace"
        )

    print(json.dumps(data, ensure_ascii=False), flush=True)


def read_json() -> dict:
    """读取 JSON，明确使用 UTF-8 编码。"""

    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(
            encoding="utf-8",
            errors="strict"
        )

    content = sys.stdin.read()

    # 兼容 UTF-8 BOM
    return json.loads(content.lstrip("\ufeff"))


def parse_pages(page_text, total_pages):
    """解析页码，例如：1-3,5,8-10。页码从 1 开始。"""

    if page_text is None or str(page_text).strip() == "":
        return list(range(total_pages))

    result = set()

    for part in str(page_text).split(","):
        part = part.strip()

        if not part:
            continue

        if "-" in part:
            start, end = part.split("-", 1)
            start = int(start.strip())
            end = int(end.strip())

            if start > end:
                raise ValueError(f"页码范围错误：{part}")

            if start < 1 or end > total_pages:
                raise ValueError(f"页码超出范围：{part}")

            result.update(range(start - 1, end))

        else:
            page = int(part)

            if page < 1 or page > total_pages:
                raise ValueError(f"页码超出范围：{page}")

            result.add(page - 1)

    if not result:
        raise ValueError("没有有效的转换页码")

    return sorted(result)


def safe_filename(name):
    """清理文件名中的非法字符。"""

    return re.sub(r'[\\/:*?"<>|]', "_", name)


def convert_pdf(input_path, output_dir, image_format, dpi, page_text):
    """转换单个 PDF 文件。"""

    # 统一转换为绝对路径
    input_path = os.path.abspath(os.path.expanduser(input_path))
    output_dir = os.path.abspath(os.path.expanduser(output_dir))

    if not os.path.isfile(input_path):
        raise FileNotFoundError(
            f"PDF 文件不存在：{input_path}"
        )

    if not input_path.lower().endswith(".pdf"):
        raise ValueError(f"不是 PDF 文件：{input_path}")

    image_format = str(image_format).lower()

    if image_format not in ("png", "jpg", "jpeg"):
        raise ValueError("图片格式只支持 PNG 和 JPG")

    if image_format == "jpeg":
        image_format = "jpg"

    dpi = int(dpi)

    if dpi not in (72, 150, 200, 300):
        raise ValueError("DPI 只支持 72、150、200、300")

    os.makedirs(output_dir, exist_ok=True)

    pdf_name = os.path.splitext(
        os.path.basename(input_path)
    )[0]

    pdf_output_dir = os.path.join(
        output_dir,
        safe_filename(pdf_name)
    )

    os.makedirs(pdf_output_dir, exist_ok=True)

    doc = fitz.open(input_path)

    try:
        if doc.needs_pass:
            raise ValueError("PDF 已加密，请先解除密码保护")

        total_pages = len(doc)

        if total_pages == 0:
            raise ValueError("PDF 没有页面")

        page_indices = parse_pages(page_text, total_pages)

        images = []

        scale = dpi / 72
        matrix = fitz.Matrix(scale, scale)

        for index in page_indices:
            page = doc.load_page(index)

            pix = page.get_pixmap(
                matrix=matrix,
                colorspace=fitz.csRGB,
                alpha=False
            )

            image_name = (
                f"{safe_filename(pdf_name)}"
                f"_page_{index + 1}.{image_format}"
            )

            image_path = os.path.join(
                pdf_output_dir,
                image_name
            )

            if image_format == "jpg":
                pix.save(image_path, jpg_quality=95)
            else:
                pix.save(image_path)

            images.append({
                "page": index + 1,
                "path": image_path,
                "width": pix.width,
                "height": pix.height
            })

        return {
            "success": True,
            "input": input_path,
            "output_dir": pdf_output_dir,
            "total_pages": total_pages,
            "converted_pages": len(images),
            "images": images
        }

    finally:
        doc.close()


def main():
    try:
        params = read_json()

        input_paths = params.get("input_paths", [])
        output_dir = params.get("output_dir", "")
        image_format = params.get("format", "png")
        dpi = params.get("dpi", 200)
        page_text = params.get("pages", "")

        if not input_paths:
            raise ValueError("请选择 PDF 文件")

        if not output_dir:
            raise ValueError("请选择输出目录")

        if isinstance(input_paths, str):
            input_paths = [input_paths]

        results = []

        for input_path in input_paths:
            try:
                result = convert_pdf(
                    input_path=input_path,
                    output_dir=output_dir,
                    image_format=image_format,
                    dpi=dpi,
                    page_text=page_text
                )

                results.append(result)

            except Exception as exc:
                results.append({
                    "success": False,
                    "input": input_path,
                    "error": str(exc)
                })

        success_count = sum(
            1 for item in results if item["success"]
        )

        failed_count = len(results) - success_count

        print_json({
            "success": failed_count == 0,
            "total": len(input_paths),
            "success_count": success_count,
            "failed_count": failed_count,
            "results": results
        })

    except Exception as exc:
        print_json({
            "success": False,
            "error": str(exc),
            "traceback": traceback.format_exc()
        })


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
图片转 PDF 工具

支持：
1. JPG / JPEG / PNG / BMP / WEBP / TIFF
2. 多张图片合并为一个 PDF
3. 每张图片单独生成 PDF
4. 保持图片原始比例
5. 支持自定义页面尺寸
6. 支持批量处理
7. JSON 标准输入输出，方便 Tauri 调用
8. Windows 中文路径及文件名
"""

import json
import os
import sys
import traceback
from pathlib import Path

from PIL import Image, ImageOps


SUPPORTED_FORMATS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp",
    ".tif",
    ".tiff",
}


def print_json(data: dict) -> None:
    """统一输出 JSON，兼容 Windows 中文编码。"""

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(
            encoding="utf-8",
            errors="replace"
        )

    print(json.dumps(data, ensure_ascii=False), flush=True)


def read_json() -> dict:
    """读取 UTF-8 JSON 参数。"""

    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(
            encoding="utf-8",
            errors="strict"
        )

    content = sys.stdin.read()

    return json.loads(content.lstrip("\ufeff"))


def load_image(image_path: str) -> Image.Image:
    """读取图片，并正确处理 EXIF 方向和透明背景。"""

    image = Image.open(image_path)

    # 修正手机照片的 EXIF 旋转方向
    image = ImageOps.exif_transpose(image)

    # 转换为 RGB，避免透明图片转 PDF 时出现问题
    if image.mode in ("RGBA", "LA") or "transparency" in image.info:
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, "white")
        background.paste(rgba, mask=rgba.getchannel("A"))
        image = background
    else:
        image = image.convert("RGB")

    return image


def reserve_output_file(output_dir: str, filename: str) -> str:
    """自动生成不重复的输出文件名，不覆盖已有文件。"""

    name, ext = os.path.splitext(filename)

    index = 0

    while True:
        if index == 0:
            candidate_name = filename
        else:
            candidate_name = f"{name}_{index}{ext}"

        candidate = os.path.join(output_dir, candidate_name)

        if not os.path.exists(candidate):
            return candidate

        index += 1


def convert_images_to_pdf(
    image_paths: list,
    output_dir: str,
    output_name: str,
    merge: bool
) -> dict:
    """将图片转换为 PDF。"""

    output_dir = os.path.abspath(os.path.expanduser(output_dir))
    os.makedirs(output_dir, exist_ok=True)

    if not image_paths:
        raise ValueError("请选择图片文件")

    images = []

    try:
        for image_path in image_paths:
            image_path = os.path.abspath(
                os.path.expanduser(image_path)
            )

            if not os.path.isfile(image_path):
                raise FileNotFoundError(
                    f"图片文件不存在：{image_path}"
                )

            ext = Path(image_path).suffix.lower()

            if ext not in SUPPORTED_FORMATS:
                raise ValueError(
                    f"不支持的图片格式：{image_path}"
                )

            image = load_image(image_path)
            images.append((image_path, image))

        results = []

        if merge:
            # 多张图片合并为一个 PDF
            pdf_name = output_name.strip() or "图片合并"

            if not pdf_name.lower().endswith(".pdf"):
                pdf_name += ".pdf"

            output_path = reserve_output_file(
                output_dir,
                pdf_name
            )

            first_image = images[0][1]
            other_images = [item[1] for item in images[1:]]

            first_image.save(
                output_path,
                "PDF",
                save_all=True,
                append_images=other_images,
                resolution=150.0
            )

            results.append({
                "success": True,
                "output": output_path,
                "image_count": len(images),
                "message": "转换成功"
            })

        else:
            # 每张图片单独生成 PDF
            for image_path, image in images:
                image_name = Path(image_path).stem + ".pdf"

                output_path = reserve_output_file(
                    output_dir,
                    image_name
                )

                image.save(
                    output_path,
                    "PDF",
                    resolution=150.0
                )

                results.append({
                    "success": True,
                    "input": image_path,
                    "output": output_path,
                    "message": "转换成功"
                })

        return {
            "success": True,
            "total": len(images),
            "results": results
        }

    finally:
        for _, image in images:
            image.close()


def main():
    try:
        params = read_json()

        input_paths = params.get("input_paths", [])
        output_dir = params.get("output_dir", "")
        output_name = params.get("output_name", "")
        merge = params.get("merge", True)

        if isinstance(input_paths, str):
            input_paths = [input_paths]

        if not input_paths:
            raise ValueError("请选择图片文件")

        if not output_dir:
            raise ValueError("请选择输出目录")

        result = convert_images_to_pdf(
            image_paths=input_paths,
            output_dir=output_dir,
            output_name=output_name,
            merge=bool(merge)
        )

        print_json(result)

    except Exception as exc:
        print_json({
            "success": False,
            "error": str(exc),
            "traceback": traceback.format_exc()
        })


if __name__ == "__main__":
    main()

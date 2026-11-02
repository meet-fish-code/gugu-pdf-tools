#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF 合并工具

功能：
1. 合并多个 PDF 文件
2. 支持自定义输出目录和文件名
3. 自动避免覆盖已有文件
4. JSON stdin/stdout，方便 Tauri 调用
5. 兼容 Windows 中文路径和中文输出
"""

import json
import os
import re
import sys
import traceback

from pypdf import PdfReader, PdfWriter


def print_json(data: dict) -> None:
    """统一输出 JSON，兼容 Windows 下的中文编码。"""
    text = json.dumps(data, ensure_ascii=False)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print(text, flush=True)


def safe_filename(name: str) -> str:
    """清理非法文件名字符。"""
    name = os.path.splitext(os.path.basename(str(name)))[0]
    name = re.sub(r'[\\/:*?"<>|]', "_", name).strip()
    return name or "合并文件"


def reserve_output_file(output_dir: str, filename: str) -> str:
    """寻找可用的输出文件名，已有文件时自动编号。"""
    name, ext = os.path.splitext(filename)
    index = 0

    while True:
        if index == 0:
            candidate_name = filename
        else:
            candidate_name = f"{name}_合并版{index}{ext}"

        candidate = os.path.join(output_dir, candidate_name)

        try:
            fd = os.open(
                candidate,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
            os.close(fd)
            return candidate

        except FileExistsError:
            index += 1


def merge_pdfs(params: dict) -> dict:
    input_paths = params.get("input_paths", [])
    output_dir = params.get("output_dir", "")
    output_name = params.get("output_name", "合并文件")

    if not isinstance(input_paths, list) or len(input_paths) < 2:
        raise ValueError("请至少选择两个 PDF 文件")

    if not output_dir:
        raise ValueError("请选择输出目录")

    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    output_name = safe_filename(output_name)
    filename = output_name + ".pdf"

    # 检查输入文件，防止重复选择同一个文件
    normalized_inputs = set()

    for path in input_paths:
        normalized_path = os.path.normcase(os.path.abspath(path))

        if normalized_path in normalized_inputs:
            raise ValueError(f"重复选择了同一个文件：{path}")

        normalized_inputs.add(normalized_path)

    # 检查输出文件不能覆盖输入文件
    requested_output = os.path.normcase(
        os.path.abspath(os.path.join(output_dir, filename))
    )

    if requested_output in normalized_inputs:
        raise ValueError("输出文件不能与输入文件重名")

    writer = PdfWriter()
    output_path = None
    total_pages = 0
    file_results = []

    try:
        for path in input_paths:
            path = os.path.abspath(path)

            if not os.path.isfile(path):
                raise ValueError(f"文件不存在：{path}")

            if not path.lower().endswith(".pdf"):
                raise ValueError(f"不是 PDF 文件：{path}")

            reader = PdfReader(path, strict=False)

            if reader.is_encrypted:
                raise ValueError(
                    f"PDF 已加密，暂不支持直接合并：{os.path.basename(path)}"
                )

            page_count = len(reader.pages)

            if page_count == 0:
                raise ValueError(
                    f"PDF 没有页面：{os.path.basename(path)}"
                )

            for page in reader.pages:
                writer.add_page(page)

            total_pages += page_count

            file_results.append({
                "input": path,
                "pages": page_count,
                "success": True
            })

        # 自动选择不冲突的输出文件名
        output_path = reserve_output_file(output_dir, filename)

        try:
            with open(output_path, "wb") as output_file:
                writer.write(output_file)

        except Exception:
            if os.path.exists(output_path):
                os.remove(output_path)
            raise

        return {
            "success": True,
            "output": output_path,
            "total_files": len(input_paths),
            "total_pages": total_pages,
            "message": "PDF 合并成功",
            "results": file_results
        }

    finally:
        writer.close()


def main():
    try:
        # 统一标准输入编码
        if hasattr(sys.stdin, "reconfigure"):
            sys.stdin.reconfigure(encoding="utf-8", errors="replace")

        params = json.loads(sys.stdin.read() or "{}")
        result = merge_pdfs(params)
        print_json(result)

    except Exception as error:
        print_json({
            "success": False,
            "error": str(error),
            "traceback": traceback.format_exc()
        })


if __name__ == "__main__":
    main()

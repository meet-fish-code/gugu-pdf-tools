#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 密码清理

移除 PDF 的编辑权限限制，并另存为新文件。
支持批量处理，通过 JSON 返回结果，方便 Tauri 调用。
"""

import json
import os
import sys
from pathlib import Path

import pikepdf


def print_json(data: dict) -> None:
    """统一输出 JSON，兼容 Windows 下的中文编码。"""
    text = json.dumps(data, ensure_ascii=False)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print(text, flush=True)


def reserve_output_file(output_folder: str, filename: str) -> str:
    """找一个可用的输出文件名，已有文件就自动编号。"""
    name, ext = os.path.splitext(filename)

    index = 0

    while True:
        if index == 0:
            candidate_name = filename
        else:
            candidate_name = f"{name}_解密版{index}{ext}"

        candidate = os.path.join(output_folder, candidate_name)

        try:
            fd = os.open(
                candidate,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
            os.close(fd)
            return candidate

        except FileExistsError:
            index += 1


def unlock_pdf(input_file: str, output_folder: str) -> dict:
    """移除 PDF 权限限制，处理结果另存为新文件。"""

    input_file = os.path.abspath(input_file)
    output_folder = os.path.abspath(output_folder)
    output_file = None

    if not os.path.isfile(input_file):
        return {
            "success": False,
            "input": input_file,
            "message": "输入文件不存在",
        }

    if not input_file.lower().endswith(".pdf"):
        return {
            "success": False,
            "input": input_file,
            "message": "不是 PDF 文件",
        }

    try:
        os.makedirs(output_folder, exist_ok=True)

        filename = os.path.basename(input_file)

        # 源文件不动，处理结果单独保存。
        output_file = reserve_output_file(output_folder, filename)

        # 这里只尝试空密码，不处理需要用户密码才能打开的文件。
        with pikepdf.open(input_file, password="") as pdf:
            pdf.save(output_file)

        return {
            "success": True,
            "input": input_file,
            "output": output_file,
            "message": "处理成功",
        }

    except pikepdf.PasswordError:
        message = "文件需要非空打开密码，无法直接处理"

    except Exception as exc:
        message = f"处理失败：{str(exc)}"

    # 失败时清理本次生成的文件。
    if output_file and os.path.exists(output_file):
        try:
            os.remove(output_file)
        except OSError:
            pass

    return {
        "success": False,
        "input": input_file,
        "message": message,
    }


def main():
    # 参数顺序：输出目录、PDF 文件列表。
    if len(sys.argv) < 3:
        print_json({
            "success": False,
            "total": 0,
            "successful": 0,
            "failed": 0,
            "results": [],
            "message": "参数不足：请提供输出目录和至少一个 PDF 文件",
        })
        sys.exit(1)

    output_folder = sys.argv[1]
    input_files = sys.argv[2:]

    results = [
        unlock_pdf(file, output_folder)
        for file in input_files
    ]

    successful = sum(item["success"] for item in results)
    failed = len(results) - successful

    print_json({
        "success": failed == 0,
        "total": len(results),
        "successful": successful,
        "failed": failed,
        "results": results,
    })


if __name__ == "__main__":
    main()
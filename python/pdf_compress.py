#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 压缩

使用 pikepdf 重新保存 PDF，尽可能减小文件体积。
支持批量处理，通过 JSON 返回处理结果，方便 Tauri 调用。
"""

import json
import os
import sys
import pikepdf


def print_json(data: dict) -> None:
    """统一输出格式，避免 Windows 下中文乱码。"""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print(json.dumps(data, ensure_ascii=False), flush=True)


def reserve_output_file(output_folder: str, filename: str) -> str:
    """生成输出文件名，重名时自动添加编号。"""
    name, ext = os.path.splitext(filename)
    index = 0

    while True:
        if index == 0:
            candidate_name = f"{name}_压缩版{ext}"
        else:
            candidate_name = f"{name}_压缩版{index}{ext}"

        candidate = os.path.join(output_folder, candidate_name)

        try:
            fd = os.open(
                candidate,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY
            )
            os.close(fd)
            return candidate
        except FileExistsError:
            index += 1


def compress_pdf(input_file: str, output_folder: str) -> dict:
    """压缩单个 PDF，返回文件信息和处理结果。"""
    input_file = os.path.abspath(input_file)
    output_folder = os.path.abspath(output_folder)

    if not os.path.isfile(input_file):
        return {
            "success": False,
            "input": input_file,
            "message": "输入文件不存在"
        }

    if not input_file.lower().endswith(".pdf"):
        return {
            "success": False,
            "input": input_file,
            "message": "文件不是 PDF 格式"
        }

    output_file = None

    try:
        os.makedirs(output_folder, exist_ok=True)

        original_size = os.path.getsize(input_file)
        filename = os.path.basename(input_file)
        output_file = reserve_output_file(output_folder, filename)

        with pikepdf.open(input_file) as pdf:
            pdf.save(
                output_file,
                compress_streams=True,
                recompress_flate=True,
                object_stream_mode=pikepdf.ObjectStreamMode.generate,
            )

        # 对比处理前后的文件大小。
        output_size = os.path.getsize(output_file)
        saved_bytes = original_size - output_size
        saved_percent = (
            round(saved_bytes / original_size * 100, 2)
            if original_size > 0 else 0
        )

        return {
            "success": True,
            "input": input_file,
            "output": output_file,
            "original_size": original_size,
            "output_size": output_size,
            "saved_bytes": saved_bytes,
            "saved_percent": saved_percent,
            "message": (
                "压缩完成"
                if saved_bytes > 0
                else "处理完成，但文件体积没有减小"
            )
        }

    except pikepdf.PasswordError:
        message = "PDF 需要密码才能打开，无法压缩"
    except Exception as exc:
        message = f"压缩失败：{str(exc)}"

    # 失败时清理已经生成的文件。
    if output_file and os.path.exists(output_file):
        try:
            os.remove(output_file)
        except OSError:
            pass

    return {
        "success": False,
        "input": input_file,
        "message": message
    }


def main():
    """读取参数，处理文件并汇总结果。"""
    if len(sys.argv) < 3:
        print_json({
            "success": False,
            "total": 0,
            "successful": 0,
            "failed": 0,
            "results": [],
            "message": "参数不足：请提供输出目录和至少一个 PDF 文件"
        })
        sys.exit(1)

    # 第一个参数是输出目录，其余参数都是待处理文件。
    output_folder = sys.argv[1]
    input_files = sys.argv[2:]

    results = [
        compress_pdf(file, output_folder)
        for file in input_files
    ]

    successful = sum(item["success"] for item in results)
    failed = len(results) - successful

    print_json({
        "success": failed == 0,
        "total": len(results),
        "successful": successful,
        "failed": failed,
        "results": results
    })


if __name__ == "__main__":
    main()
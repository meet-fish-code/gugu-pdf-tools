#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Word 转 PDF

支持批量转换 DOCX，直接调用 word2pdf 接口。
自动处理重名文件，转换结果通过 JSON 返回，方便 Tauri 调用。
"""

import json
import sys
import traceback
from pathlib import Path

from word2pdf import convert


TIMEOUT_MESSAGE = "转换失败"


def print_json(data: dict) -> None:
    """输出 JSON，兼容 Windows 下的中文编码。"""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print(json.dumps(data, ensure_ascii=False), flush=True)


def unique_output_path(path: Path) -> Path:
    """输出文件重名时自动编号，不覆盖已有文件。"""
    if not path.exists():
        return path

    index = 1

    while True:
        candidate = path.with_name(
            f"{path.stem} ({index}){path.suffix}"
        )

        if not candidate.exists():
            return candidate

        index += 1


def convert_word(source: Path, output_dir: Path) -> dict:
    """转换单个 DOCX 文件。"""
    try:
        source = source.resolve()

        if not source.is_file():
            return {
                "success": False,
                "input": str(source),
                "message": "输入文件不存在",
            }

        if source.suffix.lower() != ".docx":
            return {
                "success": False,
                "input": str(source),
                "message": "暂不支持 .doc，仅支持 .docx",
            }

        output = unique_output_path(
            output_dir / f"{source.stem}.pdf"
        )

        # 直接调用 API，不再额外启动 Python 子进程。
        result = convert(
            str(source),
            str(output),
        )

        if output.is_file() and output.stat().st_size > 0:
            return {
                "success": True,
                "input": str(source),
                "output": str(output),
                "message": "转换成功",
            }

        # 没有生成有效文件时，优先返回接口提供的警告信息。
        warnings = getattr(result, "warnings", None)
        message = (
            "; ".join(str(item) for item in warnings)
            if warnings
            else "转换程序未生成有效的 PDF 文件"
        )

        return {
            "success": False,
            "input": str(source),
            "message": message,
        }

    except Exception as exc:
        # 转换中断时，顺手清理可能留下的文件。
        try:
            if "output" in locals() and output.exists():
                output.unlink()
        except OSError:
            pass

        return {
            "success": False,
            "input": str(source),
            "message": f"转换失败：{exc}",
        }


def main() -> int:
    """读取文件列表和输出目录，完成批量转换。"""
    if len(sys.argv) < 3:
        print_json({
            "success": False,
            "total": 0,
            "successful": 0,
            "failed": 0,
            "results": [],
            "message": "参数不足：请提供至少一个 DOCX 文件和输出目录",
        })
        return 1

    output_dir = Path(sys.argv[-1]).resolve()
    input_files = [
        Path(arg)
        for arg in sys.argv[1:-1]
    ]

    try:
        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
    except OSError as exc:
        print_json({
            "success": False,
            "total": len(input_files),
            "successful": 0,
            "failed": len(input_files),
            "results": [],
            "message": f"无法创建输出目录：{exc}",
        })
        return 1

    results = [
        convert_word(source, output_dir)
        for source in input_files
    ]

    successful = sum(
        1 for item in results
        if item["success"]
    )
    failed = len(results) - successful

    print_json({
        "success": failed == 0,
        "total": len(results),
        "successful": successful,
        "failed": failed,
        "results": results,
    })

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        # 确保异常也能返回 JSON。
        print_json({
            "success": False,
            "total": 0,
            "successful": 0,
            "failed": 0,
            "results": [],
            "message": f"程序异常：{exc}",
        })
        sys.exit(1)
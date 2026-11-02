#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF 拆分工具

功能：
1. 每页拆分成一个 PDF
2. 按指定页码范围拆分，例如 1-3,4-8,9-12
3. 支持自定义输出目录和文件名
4. 自动避免覆盖已有文件
5. JSON stdin/stdout，方便 Tauri 调用
6. 兼容 Windows 中文路径和中文输出
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
    return name or "拆分文件"


def reserve_output_file(output_dir: str, filename: str) -> str:
    """寻找可用的输出文件名，已有文件时自动编号。"""
    name, ext = os.path.splitext(filename)
    index = 0

    while True:
        if index == 0:
            candidate_name = filename
        else:
            candidate_name = f"{name}_拆分版{index}{ext}"

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


def parse_ranges(value: str, total_pages: int) -> list:
    """
    解析页码范围。

    支持：
    1-3,4-8,9-12
    1,3-5,8

    页码从 1 开始。
    """

    if not isinstance(value, str) or not value.strip():
        raise ValueError("请输入拆分页码范围")

    groups = []

    for item in value.split(","):
        item = item.strip()

        if not item:
            continue

        if "-" in item:
            parts = item.split("-")

            if len(parts) != 2:
                raise ValueError(f"无效页码范围：{item}")

            try:
                start = int(parts[0].strip())
                end = int(parts[1].strip())
            except ValueError:
                raise ValueError(f"无效页码范围：{item}")

        else:
            try:
                start = end = int(item)
            except ValueError:
                raise ValueError(f"无效页码：{item}")

        if start < 1 or end < 1:
            raise ValueError("页码必须从 1 开始")

        if start > end:
            raise ValueError(f"起始页不能大于结束页：{item}")

        if end > total_pages:
            raise ValueError(
                f"页码范围 {item} 超出 PDF 总页数（{total_pages} 页）"
            )

        groups.append((start, end))

    if not groups:
        raise ValueError("没有有效的拆分页码范围")

    return groups


def write_pages(reader, start: int, end: int, output_path: str) -> None:
    """将指定页码写入一个新的 PDF，页码从 1 开始。"""

    writer = PdfWriter()

    try:
        for page_index in range(start - 1, end):
            writer.add_page(reader.pages[page_index])

        with open(output_path, "wb") as output_file:
            writer.write(output_file)

    finally:
        writer.close()


def split_pdf(params: dict) -> dict:
    input_path = params.get("input_path", "")
    output_dir = params.get("output_dir", "")
    output_name = params.get("output_name", "")
    mode = params.get("mode", "each")
    page_ranges = params.get("page_ranges", "")

    if not input_path:
        raise ValueError("请选择需要拆分的 PDF 文件")

    if not os.path.isfile(input_path):
        raise ValueError(f"文件不存在：{input_path}")

    if not input_path.lower().endswith(".pdf"):
        raise ValueError("请选择 PDF 文件")

    if not output_dir:
        raise ValueError("请选择输出目录")

    if mode not in ("each", "range"):
        raise ValueError("不支持的拆分模式")

    input_path = os.path.abspath(input_path)
    output_dir = os.path.abspath(output_dir)

    os.makedirs(output_dir, exist_ok=True)

    base_name = safe_filename(
        output_name or os.path.splitext(os.path.basename(input_path))[0]
    )

    reader = PdfReader(input_path, strict=False)

    if reader.is_encrypted:
        raise ValueError("PDF 已加密，暂不支持直接拆分")

    total_pages = len(reader.pages)

    if total_pages == 0:
        raise ValueError("PDF 没有页面")

    # 确定拆分范围
    if mode == "each":
        groups = [
            (page, page)
            for page in range(1, total_pages + 1)
        ]
    else:
        groups = parse_ranges(page_ranges, total_pages)

    results = []
    created_files = []

    try:
        for start, end in groups:

            if mode == "each":
                filename = f"{base_name}_第{start}页.pdf"
            else:
                filename = f"{base_name}_{start}-{end}页.pdf"

            # 自动避免覆盖已有文件
            output_path = reserve_output_file(output_dir, filename)
            created_files.append(output_path)

            try:
                write_pages(reader, start, end, output_path)

            except Exception:
                if os.path.exists(output_path):
                    os.remove(output_path)
                raise

            results.append({
                "success": True,
                "output": output_path,
                "start_page": start,
                "end_page": end,
                "pages": end - start + 1
            })

        return {
            "success": True,
            "input": input_path,
            "total_pages": total_pages,
            "split_count": len(results),
            "mode": mode,
            "results": results,
            "message": "PDF 拆分成功"
        }

    except Exception:
        # 失败时清理本次已经生成的文件
        for path in created_files:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

        raise


def main():
    try:
        # 统一标准输入编码
        if hasattr(sys.stdin, "reconfigure"):
            sys.stdin.reconfigure(encoding="utf-8", errors="replace")

        params = json.loads(sys.stdin.read() or "{}")

        result = split_pdf(params)

        print_json(result)

    except Exception as error:
        print_json({
            "success": False,
            "error": str(error),
            "traceback": traceback.format_exc()
        })


if __name__ == "__main__":
    main()

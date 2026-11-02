#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF 去水印工具

功能：
1. 删除 PDF 原生 Watermark 注释
2. 删除带有 GUGU_WATERMARK 专属标记的文字水印
3. 删除带有 GUGU_WATERMARK 专属标记的图片水印
4. 支持指定页面范围
5. 支持批量处理
6. 支持保留 PDF 元数据
7. 支持 JSON 标准输入输出
8. UTF-8 编码，兼容 Windows
9. 兼容 PyInstaller 打包

依赖：
pip install pypdf

重要说明：
本工具只能可靠删除：
- 由咕咕 PDF 工具箱添加了 /GUGU_WATERMARK 标记的内容流水印
- PDF 原生 /Watermark 注释

对于没有专属标记的普通文字或图片水印，
无法保证自动识别和删除。
"""

import json
import os
import sys
import traceback
import tempfile

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ContentStream,
    DecodedStreamObject,
    NameObject,
)


# ============================================================
# UTF-8 标准输入输出
# ============================================================

def configure_stdio():
    """统一标准输入输出编码为 UTF-8。"""

    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(
                encoding="utf-8",
                errors="replace",
                line_buffering=True,
            )


def output_json(data):
    """输出 JSON。"""

    sys.stdout.write(
        json.dumps(data, ensure_ascii=False) + "\n"
    )
    sys.stdout.flush()


# ============================================================
# 基础工具
# ============================================================

def validate_file(path, description):
    """检查文件是否存在。"""

    if not path:
        raise ValueError(f"未指定{description}")

    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"{description}不存在：{path}"
        )


def ensure_output_directory(output_path):
    """确保输出目录存在。"""

    directory = os.path.dirname(
        os.path.abspath(output_path)
    )

    os.makedirs(directory, exist_ok=True)


# ============================================================
# 页面范围
# ============================================================

def parse_page_ranges(value, total_pages):
    """
    解析页面范围。

    返回从 0 开始的页面索引集合。

    支持：
    all
    1
    1-3
    1,3,5
    1-3,5,8
    [1, 3, 5]
    """

    if value is None or value == "" or value == "all":
        return set(range(total_pages))

    result = set()

    if isinstance(value, (list, tuple)):
        for item in value:

            page = int(item)

            if page < 1 or page > total_pages:
                raise ValueError(
                    f"页码超出范围：{page}"
                )

            result.add(page - 1)

    else:

        for part in str(value).split(","):

            part = part.strip()

            if not part:
                continue

            if "-" in part:

                start, end = part.split("-", 1)

                start = int(start.strip())
                end = int(end.strip())

                if start > end:
                    raise ValueError(
                        f"页面范围不正确：{part}"
                    )

                if start < 1 or end > total_pages:
                    raise ValueError(
                        f"页面范围超出 PDF 页数：{part}"
                    )

                result.update(
                    range(start - 1, end)
                )

            else:

                page = int(part)

                if page < 1 or page > total_pages:
                    raise ValueError(
                        f"页码超出范围：{page}"
                    )

                result.add(page - 1)

    if not result:
        raise ValueError("没有选择有效的页面")

    return result


# ============================================================
# 专属水印标记识别
# ============================================================

WATERMARK_MARKERS = {
    "/GUGU_WATERMARK",
}


def is_watermark_operator(operands):
    """
    判断是否为水印标记。

    支持：
    1. 咕咕 PDF 专属标记 /GUGU_WATERMARK
    2. PDF 标准 Artifact Watermark 标记

    示例：

    /GUGU_WATERMARK BMC

    /Artifact <<
        /Type /Pagination
        /Subtype /Watermark
    >> BDC
    """

    if not operands:
        return False

    tag = str(operands[0])

    # 咕咕 PDF 专属水印
    if tag == "/GUGU_WATERMARK":
        return True

    # PDF Artifact 标记
    if tag == "/Artifact" and len(operands) > 1:

        properties = operands[1]

        try:
            properties = properties.get_object()
        except AttributeError:
            pass

        if hasattr(properties, "get"):

            subtype = properties.get("/Subtype")

            if str(subtype) == "/Watermark":
                return True

    return False


def remove_marked_watermarks(content_stream):
    """
    删除带有专属标记的水印内容。

    支持：
    BMC
    BDC
    EMC

    采用嵌套深度识别，避免误删水印之后的正文内容。
    """

    new_operations = []

    depth = 0
    removed_blocks = 0
    removed_operations = 0

    for operands, operator in content_stream.operations:

        if depth > 0:

            if operator in (b"BMC", b"BDC"):
                depth += 1

            elif operator == b"EMC":
                depth -= 1

            removed_operations += 1
            continue

        # 找到水印标记
        if (
            operator in (b"BMC", b"BDC")
            and is_watermark_operator(operands)
        ):

            depth = 1

            removed_blocks += 1
            removed_operations += 1

            continue

        new_operations.append(
            (operands, operator)
        )

    if depth != 0:
        raise ValueError(
            "检测到未闭合的 GUGU_WATERMARK 标记，"
            "为避免破坏 PDF，本页内容流未写回"
        )

    if removed_blocks:
        content_stream.operations = new_operations

    return removed_blocks, removed_operations


def process_page_content(page, reader):
    """
    处理单页 PDF 内容流。

    注意：
    必须在 PdfWriter.add_page() 之前处理原始 Reader 页面，
    避免 Reader 和 Writer 的对象引用关系混用。
    """

    contents = page.get("/Contents")

    if contents is None:
        return 0

    content_stream = ContentStream(
        contents,
        reader,
    )

    removed_blocks, _ = remove_marked_watermarks(
        content_stream
    )

    if removed_blocks:

        new_stream = DecodedStreamObject()

        new_stream.set_data(
            content_stream.get_data()
        )

        page[NameObject("/Contents")] = new_stream

    return removed_blocks


# ============================================================
# PDF 注释水印处理
# ============================================================

def remove_watermark_annotations(
    page,
    remove_watermark=True,
    remove_stamp=False,
    remove_all=False,
):
    """
    删除 PDF 水印注释。

    默认：
    - 删除 /Watermark 类型
    - 不删除普通 /Stamp
    - 不删除其他注释

    remove_all=True 时删除该页面全部注释。
    """

    annotations = page.get("/Annots")

    if annotations is None:
        return 0

    annotations = annotations.get_object()

    if not isinstance(annotations, (list, tuple)):
        return 0

    remaining = []
    removed = 0

    for annotation_ref in annotations:

        annotation = annotation_ref.get_object()

        subtype = str(
            annotation.get("/Subtype", "")
        )

        should_remove = (
            remove_all
            or (
                remove_watermark
                and subtype == "/Watermark"
            )
            or (
                remove_stamp
                and subtype == "/Stamp"
            )
        )

        if should_remove:
            removed += 1
        else:
            remaining.append(annotation_ref)

    if removed:

        if remaining:
            page[NameObject("/Annots")] = remaining

        else:
            del page[NameObject("/Annots")]

    return removed


# ============================================================
# 元数据
# ============================================================

def get_document_metadata(reader):
    """获取 PDF 文档元数据。"""

    if not reader.metadata:
        return {}

    metadata = {}

    for key, value in reader.metadata.items():

        if value is None:
            continue

        key = str(key)

        if key.startswith("/"):
            metadata[key] = str(value)

    return metadata


# ============================================================
# 单个 PDF 处理
# ============================================================

def remove_pdf_watermark(params):
    """处理单个 PDF 文件。"""

    input_path = params.get("input_path")
    output_path = params.get("output_path")

    validate_file(
        input_path,
        "输入 PDF 文件",
    )

    if not output_path:
        raise ValueError("未指定输出 PDF 路径")

    input_abs = os.path.normcase(
        os.path.abspath(input_path)
    )

    output_abs = os.path.normcase(
        os.path.abspath(output_path)
    )

    if input_abs == output_abs:
        raise ValueError(
            "输入文件和输出文件不能相同，"
            "请指定其他输出路径"
        )

    ensure_output_directory(output_path)

    reader = PdfReader(
        input_path,
        strict=False,
    )

    # ========================================================
    # PDF 解密
    # ========================================================

    if reader.is_encrypted:

        password = params.get("password", "")

        if not password:
            raise ValueError(
                "PDF 已加密，请提供打开密码"
            )

        decrypt_result = reader.decrypt(password)

        if not decrypt_result:
            raise ValueError(
                "PDF 密码错误，无法处理"
            )

    total_pages = len(reader.pages)

    if total_pages <= 0:
        raise ValueError("PDF 不包含有效页面")

    page_indexes = parse_page_ranges(
        params.get("page_ranges", "all"),
        total_pages,
    )

    remove_marked = bool(
        params.get(
            "remove_marked_watermarks",
            True,
        )
    )

    remove_watermark = bool(
        params.get(
            "remove_watermark_annotations",
            True,
        )
    )

    remove_stamp = bool(
        params.get(
            "remove_stamp_annotations",
            False,
        )
    )

    remove_all_annotations = bool(
        params.get(
            "remove_all_annotations",
            False,
        )
    )

    # ========================================================
    # 关键修复：先修改 Reader 页面
    # ========================================================

    marked_count = 0
    annotation_count = 0

    for page_index in sorted(page_indexes):

        page = reader.pages[page_index]

        # 删除内容流水印
        if remove_marked:

            marked_count += process_page_content(
                page,
                reader,
            )

        # 删除注释水印
        annotation_count += remove_watermark_annotations(
            page,
            remove_watermark=remove_watermark,
            remove_stamp=remove_stamp,
            remove_all=remove_all_annotations,
        )

    # ========================================================
    # 创建 Writer
    # ========================================================

    writer = PdfWriter()

    # 所有 Reader 页面处理完成后，再添加到 Writer
    for page in reader.pages:
        writer.add_page(page)

    # ========================================================
    # 保留元数据
    # ========================================================

    metadata = get_document_metadata(reader)

    if metadata:
        writer.add_metadata(metadata)

    # ========================================================
    # 保存 PDF
    # ========================================================

    output_directory = os.path.dirname(
        os.path.abspath(output_path)
    )

    temp_fd, temp_output_path = tempfile.mkstemp(
        prefix="gugu_pdf_",
        suffix=".tmp",
        dir=output_directory,
    )

    os.close(temp_fd)

    try:

        with open(temp_output_path, "wb") as file:
            writer.write(file)

        # 写入成功后再替换目标文件
        os.replace(
            temp_output_path,
            output_path,
        )

    except Exception:

        if os.path.exists(temp_output_path):
            try:
                os.remove(temp_output_path)
            except OSError:
                pass

        raise

    return {
        "success": True,
        "input_path": input_path,
        "output_path": output_path,
        "total_pages": total_pages,
        "processed_pages": len(page_indexes),
        "removed_watermark_blocks": marked_count,
        "removed_annotations": annotation_count,
        "message": (
            f"处理完成，共检查 {len(page_indexes)} 页，"
            f"移除水印内容块 {marked_count} 个，"
            f"移除注释 {annotation_count} 个。"
        ),
    }


# ============================================================
# 批量处理
# ============================================================

def process_batch(params):
    """批量处理 PDF 文件。"""

    files = params.get("files")

    # 兼容单文件输入
    if not files:

        files = [{
            "input_path": params.get("input_path"),
            "output_path": params.get("output_path"),
        }]

    if not isinstance(files, list) or not files:
        raise ValueError("没有需要处理的 PDF 文件")

    results = []

    for item in files:

        if not isinstance(item, dict):

            results.append({
                "success": False,
                "message": "批量文件参数必须是 JSON 对象",
            })

            continue

        current_params = dict(params)

        current_params.update(item)

        try:

            result = remove_pdf_watermark(
                current_params
            )

            results.append(result)

        except Exception as error:

            results.append({
                "success": False,
                "input_path": item.get("input_path"),
                "output_path": item.get("output_path"),
                "message": str(error),
                "traceback": traceback.format_exc(),
            })

    successful = sum(
        1 for item in results
        if item.get("success")
    )

    failed = len(results) - successful

    return {
        "success": failed == 0,
        "total": len(results),
        "successful": successful,
        "failed": failed,
        "results": results,
        "message": (
            f"去水印处理完成：成功 {successful} 个，"
            f"失败 {failed} 个。"
        ),
    }


# ============================================================
# 主入口
# ============================================================

def main():

    configure_stdio()

    try:

        raw = sys.stdin.read()

        if not raw.strip():
            raise ValueError("未接收到处理参数")

        params = json.loads(raw)

        if not isinstance(params, dict):
            raise ValueError("输入参数必须是 JSON 对象")

        result = process_batch(params)

        output_json(result)

        if not result["success"]:
            sys.exit(1)

    except Exception as error:

        output_json({
            "success": False,
            "message": str(error),
            "traceback": traceback.format_exc(),
        })

        sys.exit(1)


if __name__ == "__main__":
    main()
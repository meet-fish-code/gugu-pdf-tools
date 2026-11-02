#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PDF 水印工具

功能：
1. 文字水印
2. 图片水印
3. 页面上方 / 页面下方
4. 居中水印 / 全页平铺水印
5. 透明度设置
6. 旋转角度设置
7. 文字颜色、字体大小设置
8. 图片宽度设置
9. 指定页面范围
10. 保留 PDF 元数据
11. JSON 标准输入输出
12. UTF-8 编码，解决 Windows 中文乱码
13. 兼容 PyInstaller 打包

依赖：
pip install pypdf reportlab pillow

文字水印 JSON 示例：

{
    "input_path": "D:/test/原始文件.pdf",
    "output_path": "D:/test/文字水印.pdf",
    "watermark_type": "text",
    "text": "内部资料",
    "font_size": 48,
    "font_path": "C:/Windows/Fonts/msyh.ttc",
    "color": "#999999",
    "opacity": 0.2,
    "rotation": 45,
    "position": "tile",
    "layer": "foreground",
    "page_ranges": "all"
}

图片水印 JSON 示例：

{
    "input_path": "D:/test/原始文件.pdf",
    "output_path": "D:/test/图片水印.pdf",
    "watermark_type": "image",
    "image_path": "D:/test/logo.png",
    "image_width": 150,
    "opacity": 0.3,
    "rotation": 0,
    "position": "center",
    "layer": "background",
    "page_ranges": "all"
}

参数说明：

watermark_type:
    text        文字水印
    image       图片水印

position:
    center      页面居中
    tile        全页平铺

layer:
    foreground  页面上方，水印覆盖正文
    background  页面下方，水印位于正文后面

page_ranges:
    all         所有页面
    1           第 1 页
    1-3         第 1 到 3 页
    1,3,5       第 1、3、5 页
    1-3,5,8-10  组合范围

输出约定：
stdout 只输出 JSON
stderr 用于调试信息
所有标准输入输出均使用 UTF-8
"""


import io
import json
import os
import sys
import traceback

from PIL import Image
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader


# ============================================================
# UTF-8 标准输入输出处理
# ============================================================

def configure_stdio():
    """统一标准输入输出编码为 UTF-8。"""

    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(
            encoding="utf-8",
            errors="replace",
        )

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(
            encoding="utf-8",
            errors="replace",
            line_buffering=True,
        )

    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(
            encoding="utf-8",
            errors="replace",
            line_buffering=True,
        )


def output_json(data):
    """只通过 stdout 输出 UTF-8 JSON。"""

    result = json.dumps(
        data,
        ensure_ascii=False,
    )

    sys.stdout.write(result + "\n")
    sys.stdout.flush()


def success(data):
    """输出成功结果。"""

    output_json(data)


def failure(error):
    """输出失败结果。"""

    output_json({
        "success": False,
        "message": str(error),
        "traceback": traceback.format_exc(),
    })

    sys.exit(1)


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


def clamp(value, minimum, maximum):
    """限制数值范围。"""

    return max(
        minimum,
        min(maximum, value),
    )


# ============================================================
# 字体处理
# ============================================================

def find_chinese_font(custom_path=None):
    """查找可用的中文字体。"""

    if custom_path:
        validate_file(
            custom_path,
            "字体文件",
        )

        return custom_path

    candidates = [
        r"C:\Windows\Fonts\msyh.ttf",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttf",
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simsun.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    ]

    for path in candidates:
        if os.path.isfile(path):
            return path

    raise FileNotFoundError(
        "未找到可用的中文字体，请通过 font_path 参数指定 TTF 字体文件"
    )


def register_watermark_font(font_path=None, font_index=0):
    """注册水印字体，支持 TTC 字体索引。"""

    path = find_chinese_font(font_path)
    font_index = int(font_index or 0)

    if font_index < 0:
        raise ValueError("字体索引不能小于 0")

    try:
        try:
            font = TTFont(
                "WatermarkFont",
                path,
                subfontIndex=font_index,
            )

        except TypeError:
            # 兼容不支持 subfontIndex 参数的旧版本 ReportLab
            if font_index != 0:
                raise RuntimeError(
                    "当前 ReportLab 版本不支持 TTC 多字体面，"
                    "请升级 ReportLab 或使用独立 TTF 字体文件。"
                )

            font = TTFont(
                "WatermarkFont",
                path,
            )

        pdfmetrics.registerFont(font)

        return "WatermarkFont"

    except Exception as e:
        raise RuntimeError(
            f"字体加载失败：{e}，"
            f"字体文件：{path}，"
            f"字体索引：{font_index}。"
            "建议使用包含中文字符的 TTF 字体。"
        )

# ============================================================
# 页面范围处理
# ============================================================

def parse_page_ranges(value, total_pages):
    """
    解析页面范围。

    支持：
    all
    1
    1,3,5
    1-3
    1,3-5,8

    页码从 1 开始。
    返回 Python 页面索引集合。
    """

    if value is None or value == "" or value == "all":
        return set(range(total_pages))

    if isinstance(value, list):

        result = set()

        for item in value:

            page = int(item)

            if page < 1 or page > total_pages:
                raise ValueError(
                    f"页码超出范围：{page}"
                )

            result.add(page - 1)

        if not result:
            raise ValueError("没有选择有效的页面")

        return result

    result = set()

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
# 文字水印
# ============================================================

def make_text_overlay(
    page_width,
    page_height,
    text,
    font_name,
    font_size,
    color,
    opacity,
    rotation,
    position,
):
    """生成文字水印 PDF 图层。"""

    buffer = io.BytesIO()

    pdf = canvas.Canvas(
        buffer,
        pagesize=(
            page_width,
            page_height,
        ),
        pageCompression=1,
    )
    pdf._code.append("/GUGU_WATERMARK BMC")
    pdf.saveState()

    pdf.setFont(
        font_name,
        font_size,
    )

    pdf.setFillColor(
        HexColor(color)
    )

    pdf.setFillAlpha(opacity)

    text_width = pdfmetrics.stringWidth(
        text,
        font_name,
        font_size,
    )

    if position == "center":

        pdf.translate(
            page_width / 2,
            page_height / 2,
        )

        pdf.rotate(rotation)

        pdf.drawString(
            -text_width / 2,
            -font_size / 3,
            text,
        )

    elif position == "tile":

        step_x = max(
            text_width * 1.8,
            150,
        )

        step_y = max(
            font_size * 3.5,
            120,
        )

        y = -page_height

        while y < page_height * 2:

            x = -page_width

            while x < page_width * 2:

                pdf.saveState()

                pdf.translate(x, y)
                pdf.rotate(rotation)

                pdf.drawString(
                    0,
                    0,
                    text,
                )

                pdf.restoreState()

                x += step_x

            y += step_y

    else:

        raise ValueError(
            "position 只能是 center 或 tile"
        )

    pdf.restoreState()

    # 结束咕咕 PDF 专属水印标记
    pdf._code.append("EMC")

    pdf.save()

    buffer.seek(0)

    return PdfReader(buffer).pages[0]


# ============================================================
# 图片水印
# ============================================================

def load_watermark_image(image_path, opacity):
    """读取图片并调整透明度。"""

    validate_file(
        image_path,
        "水印图片",
    )

    opacity = clamp(
        float(opacity),
        0.0,
        1.0,
    )

    image = Image.open(
        image_path
    ).convert("RGBA")

    if image.width <= 0 or image.height <= 0:
        raise ValueError("水印图片尺寸无效")

    alpha = image.getchannel("A")

    alpha = alpha.point(
        lambda value: int(value * opacity)
    )

    image.putalpha(alpha)

    return image


def make_image_overlay(
    page_width,
    page_height,
    image_path,
    image_width,
    opacity,
    rotation,
    position,
):
    """生成图片水印 PDF 图层。"""

    image = load_watermark_image(
        image_path,
        opacity,
    )

    original_width, original_height = image.size

    image_width = float(image_width)

    if image_width <= 0:
        raise ValueError(
            "图片宽度必须大于 0"
        )

    scale = image_width / original_width

    draw_width = original_width * scale
    draw_height = original_height * scale

    image_buffer = io.BytesIO()

    image.save(
        image_buffer,
        format="PNG",
    )

    image_buffer.seek(0)

    image_reader = ImageReader(
        image_buffer
    )

    buffer = io.BytesIO()

    pdf = canvas.Canvas(
        buffer,
        pagesize=(
            page_width,
            page_height,
        ),
        pageCompression=1,
    )

    if position == "center":

        pdf.saveState()

        pdf.translate(
            page_width / 2,
            page_height / 2,
        )

        pdf.rotate(rotation)

        pdf.drawImage(
            image_reader,
            -draw_width / 2,
            -draw_height / 2,
            width=draw_width,
            height=draw_height,
            mask="auto",
        )

        pdf.restoreState()

    elif position == "tile":

        step_x = max(
            draw_width * 1.8,
            100,
        )

        step_y = max(
            draw_height * 1.8,
            100,
        )

        y = -page_height

        while y < page_height * 2:

            x = -page_width

            while x < page_width * 2:

                pdf.saveState()

                pdf.translate(
                    x,
                    y,
                )

                pdf.rotate(rotation)

                pdf.drawImage(
                    image_reader,
                    0,
                    0,
                    width=draw_width,
                    height=draw_height,
                    mask="auto",
                )

                pdf.restoreState()

                x += step_x

            y += step_y

    else:

        raise ValueError(
            "position 只能是 center 或 tile"
        )

    pdf.save()

    buffer.seek(0)

    return PdfReader(buffer).pages[0]


# ============================================================
# PDF 水印主逻辑
# ============================================================

def add_watermark(params):
    """执行 PDF 水印处理。"""

    input_path = params.get(
        "input_path"
    )

    output_path = params.get(
        "output_path"
    )

    watermark_type = params.get(
        "watermark_type",
        "text",
    )

    # --------------------------------------------------------
    # 输入输出检查
    # --------------------------------------------------------

    validate_file(
        input_path,
        "输入 PDF 文件",
    )

    if not output_path:
        raise ValueError(
            "未指定输出文件路径"
        )

    if os.path.splitext(input_path)[1].lower() != ".pdf":
        raise ValueError(
            "输入文件必须是 PDF"
        )

    if os.path.splitext(output_path)[1].lower() != ".pdf":
        raise ValueError(
            "输出文件扩展名必须是 .pdf"
        )

    if os.path.abspath(input_path) == os.path.abspath(output_path):
        raise ValueError(
            "输出文件不能与原文件相同"
        )

    output_dir = os.path.dirname(
        os.path.abspath(output_path)
    )

    os.makedirs(
        output_dir,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # 读取 PDF
    # --------------------------------------------------------

    reader = PdfReader(
        input_path
    )

    if reader.is_encrypted:
        raise ValueError(
            "暂不支持加密 PDF，请先解除 PDF 密码保护"
        )

    total_pages = len(reader.pages)

    if total_pages == 0:
        raise ValueError(
            "PDF 没有页面"
        )

    target_pages = parse_page_ranges(
        params.get(
            "page_ranges",
            "all",
        ),
        total_pages,
    )

    # --------------------------------------------------------
    # 水印公共参数
    # --------------------------------------------------------

    position = params.get(
        "position",
        "center",
    )

    layer = params.get(
        "layer",
        "foreground",
    )

    if position not in (
        "center",
        "tile",
    ):
        raise ValueError(
            "position 只能是 center 或 tile"
        )

    if layer not in (
        "foreground",
        "background",
    ):
        raise ValueError(
            "layer 只能是 foreground 或 background"
        )

    opacity = clamp(
        float(
            params.get(
                "opacity",
                0.2,
            )
        ),
        0.0,
        1.0,
    )

    rotation = float(
        params.get(
            "rotation",
            45,
        )
    )

    # --------------------------------------------------------
    # 文字水印配置
    # --------------------------------------------------------

    if watermark_type == "text":

        text = str(
            params.get(
                "text",
                "",
            )
        ).strip()

        if not text:
            raise ValueError(
                "水印文字不能为空"
            )

        font_size = float(
            params.get(
                "font_size",
                48,
            )
        )

        if font_size <= 0:
            raise ValueError(
                "字体大小必须大于 0"
            )

        color = params.get(
            "color",
            "#999999",
        )

        try:
            HexColor(color)
        except Exception:
            raise ValueError(
                "颜色格式错误，请使用 #RRGGBB 格式"
            )

        font_name = register_watermark_font(
            font_path=params.get("font_path"),
            font_index=params.get("font_index", 0),
        )

    # --------------------------------------------------------
    # 图片水印配置
    # --------------------------------------------------------

    elif watermark_type == "image":

        image_path = params.get(
            "image_path"
        )

        validate_file(
            image_path,
            "水印图片",
        )

        image_width = float(
            params.get(
                "image_width",
                150,
            )
        )

        if image_width <= 0:
            raise ValueError(
                "图片宽度必须大于 0"
            )

    else:

        raise ValueError(
            "watermark_type 只能是 text 或 image"
        )

    # --------------------------------------------------------
    # 逐页添加水印
    # --------------------------------------------------------

    writer = PdfWriter()

    for index, page in enumerate(reader.pages):

        if index in target_pages:

            page_width = float(
                page.mediabox.width
            )

            page_height = float(
                page.mediabox.height
            )

            if watermark_type == "text":

                overlay = make_text_overlay(
                    page_width=page_width,
                    page_height=page_height,
                    text=text,
                    font_name=font_name,
                    font_size=font_size,
                    color=color,
                    opacity=opacity,
                    rotation=rotation,
                    position=position,
                )

            else:

                overlay = make_image_overlay(
                    page_width=page_width,
                    page_height=page_height,
                    image_path=image_path,
                    image_width=image_width,
                    opacity=opacity,
                    rotation=rotation,
                    position=position,
                )

            # 页面上方 / 页面下方
            if layer == "foreground":

                page.merge_page(
                    overlay,
                    over=True,
                )

            else:

                page.merge_page(
                    overlay,
                    over=False,
                )

        writer.add_page(page)

    # --------------------------------------------------------
    # 保留 PDF 元数据
    # --------------------------------------------------------

    if reader.metadata:

        metadata = {}

        for key, value in reader.metadata.items():

            if value is not None:
                metadata[str(key)] = str(value)

        if metadata:
            writer.add_metadata(
                metadata
            )

    # --------------------------------------------------------
    # 输出 PDF
    # --------------------------------------------------------

    temp_path = output_path + ".tmp"

    try:

        with open(
            temp_path,
            "wb",
        ) as file:

            writer.write(file)

        os.replace(
            temp_path,
            output_path,
        )

    finally:

        if os.path.exists(temp_path):
            os.remove(temp_path)

    return {
        "success": True,
        "message": "水印添加成功",
        "output_path": output_path,
        "total_pages": total_pages,
        "watermarked_pages": len(target_pages),
        "watermark_type": watermark_type,
        "position": position,
        "layer": layer,
    }


# ============================================================
# 程序入口
# ============================================================

def main():

    configure_stdio()

    try:

        raw = sys.stdin.read()

        if not raw.strip():
            raise ValueError(
                "没有收到 JSON 参数"
            )

        params = json.loads(
            raw
        )

        if not isinstance(params, dict):
            raise ValueError(
                "JSON 参数必须是对象"
            )

        result = add_watermark(
            params
        )

        success(
            result
        )

    except Exception as error:

        failure(
            error
        )


if __name__ == "__main__":

    main()

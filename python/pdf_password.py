#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 密码保护

支持设置打开密码、编辑权限密码，也可以两种一起设置。
通过标准输入接收 JSON 参数，处理结果通过标准输出返回，方便 Tauri 调用。
"""

import json
import os
import sys
import traceback

from pypdf import PdfReader, PdfWriter
from pypdf.constants import UserAccessPermissions


def write_json(data: dict) -> None:
    """输出 UTF-8 JSON，避免 Windows 下管道编码不一致。"""
    output = json.dumps(data, ensure_ascii=False)
    sys.stdout.buffer.write(output.encode("utf-8") + b"\n")
    sys.stdout.buffer.flush()


def read_json() -> dict:
    """读取并解析标准输入中的 JSON 参数。"""
    raw = sys.stdin.buffer.read()
    if not raw:
        raise ValueError("没有收到加密参数，请传入 JSON")

    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"JSON 参数解析失败：{exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("参数格式错误：JSON 顶层必须是对象")

    return data


def protect_pdf(
    input_path: str,
    output_path: str,
    mode: str,
    user_password: str = "",
    owner_password: str = "",
    allow_print: bool = True,
    allow_copy: bool = False,
    allow_modify: bool = False,
) -> dict:
    """设置 PDF 密码和访问权限。"""

    if not input_path:
        raise ValueError("请输入 PDF 文件路径")

    if not output_path:
        raise ValueError("请指定输出 PDF 文件路径")

    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"输入 PDF 文件不存在：{input_path}")

    if not input_path.lower().endswith(".pdf"):
        raise ValueError("输入文件必须是 PDF")

    if not output_path.lower().endswith(".pdf"):
        raise ValueError("输出文件必须是 PDF")

    input_abs = os.path.normcase(os.path.abspath(input_path))
    output_abs = os.path.normcase(os.path.abspath(output_path))

    if input_abs == output_abs:
        raise ValueError("输出路径不能与输入路径相同，请另存为新文件")

    if mode not in ("view", "edit", "both"):
        raise ValueError("mode 必须是 view、edit 或 both")

    if mode in ("view", "both") and not user_password:
        raise ValueError("请设置查看密码")

    if mode in ("edit", "both") and not owner_password:
        raise ValueError("请设置编辑权限密码")

    user_pwd = user_password if mode in ("view", "both") else ""
    owner_pwd = owner_password if mode in ("edit", "both") else ""

    if owner_pwd and owner_pwd == user_pwd:
        raise ValueError("查看密码和编辑权限密码不能相同")

    output_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(output_dir, exist_ok=True)

    temp_path = output_path + ".tmp"

    try:
        reader = PdfReader(input_path, strict=False)

        if reader.is_encrypted:
            raise ValueError("该 PDF 已加密，请先解除原有密码保护")

        writer = PdfWriter()
        writer.append_pages_from_reader(reader)

        # 原文件有元数据的话，一并带到新文件中。
        if reader.metadata:
            metadata = {
                str(key): str(value)
                for key, value in reader.metadata.items()
                if key and value is not None
            }
            if metadata:
                writer.add_metadata(metadata)

        # 根据用户选择组合 PDF 权限。
        permissions = UserAccessPermissions(0)

        if allow_print:
            permissions |= UserAccessPermissions.PRINT
            permissions |= UserAccessPermissions.PRINT_TO_REPRESENTATION

        if allow_copy:
            permissions |= UserAccessPermissions.EXTRACT
            permissions |= UserAccessPermissions.EXTRACT_TEXT_AND_GRAPHICS

        if allow_modify:
            permissions |= UserAccessPermissions.MODIFY
            permissions |= UserAccessPermissions.ANNOTATE
            permissions |= UserAccessPermissions.FILL_FORM_FIELDS
            permissions |= UserAccessPermissions.ASSEMBLE_DOC

        writer.encrypt(
            user_password=user_pwd,
            owner_password=owner_pwd or None,
            permissions_flag=permissions,
            algorithm="AES-256",
        )

        # 先写临时文件，确认加密正常后再替换正式文件。
        try:
            with open(temp_path, "wb") as output_file:
                writer.write(output_file)

            check_reader = PdfReader(temp_path, strict=False)

            if not check_reader.is_encrypted:
                raise RuntimeError("生成的 PDF 未正确加密")

            # 再用查看密码试一次，避免生成的文件无法正常打开。
            if user_pwd:
                if not check_reader.decrypt(user_pwd):
                    raise RuntimeError("生成的 PDF 无法使用查看密码解锁")

            os.replace(temp_path, output_path)

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

        return {
            "success": True,
            "input_path": input_path,
            "output_path": output_path,
            "mode": mode,
            "algorithm": "AES-256",
            "message": "PDF 密码保护设置成功",
        }

    finally:
        reader = None


def main() -> int:
    try:
        params = read_json()

        result = protect_pdf(
            input_path=str(params.get("input_path", "")),
            output_path=str(params.get("output_path", "")),
            mode=str(params.get("mode", "")),
            user_password=str(params.get("user_password", "")),
            owner_password=str(params.get("owner_password", "")),
            allow_print=bool(params.get("allow_print", True)),
            allow_copy=bool(params.get("allow_copy", False)),
            allow_modify=bool(params.get("allow_modify", False)),
        )

        write_json(result)
        return 0

    except Exception as exc:
        # 堆栈信息只写入 stderr，stdout 留给 JSON 返回结果。
        print(
            f"PDF 密码保护失败：{exc}",
            file=sys.stderr,
            flush=True,
        )
        traceback.print_exc(file=sys.stderr)

        try:
            write_json({
                "success": False,
                "error": str(exc),
            })
        except Exception:
            pass

        return 1


if __name__ == "__main__":
    sys.exit(main())
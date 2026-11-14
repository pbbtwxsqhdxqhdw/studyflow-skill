"""Check StudyFlow v1 references and write a verified ZIP."""
import argparse
import json
import math
from pathlib import Path
import re
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile

IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
MIME_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
MIB = 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def index(items, label):
    require(isinstance(items, list), f"{label} 必须是数组")
    result = {}
    for item in items:
        identifier = item["id"]
        require(IDENTIFIER.fullmatch(identifier), f"{label} ID 无效：{identifier}")
        require(identifier not in result, f"{label} ID 重复：{identifier}")
        result[identifier] = item
    return result


def validate(manifest, directory):
    require(type(manifest["version"]) is int and manifest["version"] == 1, "version 应为 1")
    questions = index(manifest["questions"], "题目")
    materials = index(manifest["materials"], "材料")
    assets = index(manifest["assets"], "图片")
    exams = index(manifest["exams"], "练习")
    require(0 < len(questions) <= 10000, "题目数量应为 1 至 10,000")
    require(exams, "请为可作答题目建立至少一套练习")

    ready = set()
    for key, question in questions.items():
        kind = question["type"]
        require(kind in {"blank", "single", "multiple", "judge"}, f"{key} 题型无效")
        require("stem" in question and str(question["stem"]).strip(), f"{key} 缺少题干")
        material_id = question.get("materialId")
        require(material_id is None or material_id in materials, f"{key} 引用了不存在的材料")
        choices = index(question["options"], f"{key} 的选项")
        answers = question["answer"]
        require(isinstance(answers, list) and all(isinstance(x, str) for x in answers), f"{key} 答案应是字符串数组")
        if "blankNumbers" in question:
            numbers = question["blankNumbers"]
            require(isinstance(numbers, list) and len(numbers) == (len(answers) if kind == "blank" else 1)
                    and all(type(n) is int and 0 < n < 2**53 for n in numbers)
                    and len(set(numbers)) == len(numbers), f"{key} 空号无效")
        if question.get("draft") is True:
            continue
        require(answers and all(x.strip() for x in answers), f"{key} 缺少答案")
        if kind == "blank":
            require(not choices, f"{key} 填空不应有选项")
            if "accepted" in question:
                accepted = question["accepted"]
                require(isinstance(accepted, list) and len(accepted) == len(answers)
                        and all(isinstance(group, list) and answer in group
                                and all(isinstance(x, str) and x.strip() for x in group)
                                for answer, group in zip(answers, accepted)), f"{key} 等价答案无效")
        else:
            require(len(choices) >= 2 and set(answers) <= choices.keys()
                    and len(set(answers)) == len(answers), f"{key} 选项与答案不对应")
            require(kind == "multiple" or len(answers) == 1, f"{key} 应只有一个正确选项")
            require(kind != "judge" or choices.keys() == {"T", "F"}, f"{key} 判断题需选项 T、F")
        ready.add(key)

    covered = set()
    for key, exam in exams.items():
        ids = exam["questionIds"]
        points = exam["points"]
        require(isinstance(ids, list) and ids and len(set(ids)) == len(ids) and set(ids) <= ready,
                f"{key} 练习中有草稿、重复题或无效题号")
        require(isinstance(points, list) and len(ids) == len(points)
                and all(type(p) in (int, float) and math.isfinite(p) and p > 0 for p in points),
                f"{key} 分值须与题目一一对应且为正数")
        covered.update(ids)
    require(ready == covered, f"练习未收录的可作答题：{', '.join(sorted(ready - covered))}")

    for item in [*questions.values(), *materials.values()]:
        fields = [item.get(key) for key in ("stem", "analysis", "hint", "content")]
        fields.extend(opt.get("content") for opt in item.get("options", []))
        for field in fields:
            if isinstance(field, list):
                for block in field:
                    if block["type"] == "image":
                        require(block.get("assetId") in assets, f"{item['id']} 中的图片未声明")

    paths = {}
    for asset in assets.values():
        path = asset["path"]
        parts = path.split("/")
        require(re.fullmatch(r"assets/[A-Za-z0-9._/-]+", path)
                and not any(part in {"", ".", ".."} for part in parts), f"图片路径无效：{path}")
        file = (directory / path).resolve()
        require(file.is_relative_to(directory) and file.is_file(), f"缺少图片：{path}")
        require(0 < file.stat().st_size <= 15 * MIB and asset["mime"] in MIME_TYPES,
                f"图片大小或 MIME 类型无效：{path}")
        require(path not in paths, f"图片路径重复：{path}")
        paths[path] = file
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        require(args.output.suffix.lower() == ".zip", "输出文件须为 .zip")
        require(args.manifest.resolve() != args.output.resolve(), "清单与输出不能指向同一文件")
        raw = args.manifest.read_text(encoding="utf-8")
        manifest = json.loads(raw)
        paths = validate(manifest, args.manifest.resolve().parent)
        require(args.output.resolve() not in paths.values(), "输出不能覆盖图片")
        with tempfile.TemporaryDirectory(dir=args.output.parent) as staging:
            temporary = Path(staging) / "pack.zip"
            with ZipFile(temporary, "w", ZIP_DEFLATED) as archive:
                archive.writestr("manifest.json", raw)
                for name, file in paths.items():
                    archive.write(file, name)
            require(temporary.stat().st_size <= 50 * MIB, "题包超过 50 MB")
            with ZipFile(temporary) as archive:
                require(archive.testzip() is None, "ZIP 完整性校验失败")
                require(json.loads(archive.read("manifest.json")) == manifest, "ZIP 清单核对失败")
            temporary.replace(args.output)
    except (KeyError, OSError, TypeError, ValueError, OverflowError) as error:
        parser.exit(1, f"题包检查失败：{error}\n")
    print(f"已生成 {args.output}（{len(manifest['exams'])} 套练习）")


if __name__ == "__main__":
    main()

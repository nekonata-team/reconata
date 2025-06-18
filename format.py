import argparse
from pathlib import Path

from container import container

formatter = container.formatter()


def format_md_file(md_path: Path):
    with md_path.open("r", encoding="utf-8") as f:
        content = f.read()
    formatted = formatter.format(content)
    if formatted != content:
        with md_path.open("w", encoding="utf-8") as f:
            f.write(formatted)
        print(f"Formatted: {md_path}")
    else:
        print(f"No change: {md_path}")


def format_md_files_in_dir(directory: Path):
    for md_file in directory.rglob("*.md"):
        format_md_file(md_file)


def main():
    parser = argparse.ArgumentParser(
        description="指定フォルダ配下の.mdファイルをフォーマットします"
    )
    parser.add_argument("directory", type=Path, help="フォーマット対象のディレクトリ")
    args = parser.parse_args()
    if not args.directory.is_dir():
        print(f"{args.directory} はディレクトリではありません")
        return
    format_md_files_in_dir(args.directory)


if __name__ == "__main__":
    main()

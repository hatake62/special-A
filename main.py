from pathlib import Path

from src import run_src


if __name__ == "__main__":
    demo_src = Path("examples/demo.src").read_text(encoding="utf-8")
    print("== デモ実行 ==")
    run_src(demo_src)

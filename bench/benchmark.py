import statistics
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src import BaseVM, VM, build  # noqa: E402
from bench.programs import (  # noqa: E402
    ARRAY_SUM_BENCH_SRC,
    CALL_BENCH_SRC,
    CONSTANT_FOLD_ARRAY_BENCH_SRC,
    EXCEPTION_BENCH_SRC,
    INLINE_ARRAY_BENCH_SRC,
    TRY_NO_EXCEPTION_BENCH_SRC,
)


def benchmark(label, src, vm_class, optimize=False, repeat=5):
    functions = build(src, optimize=optimize)
    times = []
    instruction_counts = []
    for _ in range(repeat):
        vm = vm_class(functions)
        start = time.perf_counter()
        vm.run()
        times.append(time.perf_counter() - start)
        instruction_counts.append(vm.instruction_count)

    return {
        "label": label,
        "optimize": optimize,
        "min": min(times),
        "avg": statistics.mean(times),
        "instructions": instruction_counts[0],
    }


def print_source_block(title, src):
    print(f"== 元となるベンチマークプログラム: {title} ==")
    print(src.strip())
    print()


def print_benchmark_programs():
    print_source_block("関数呼び出し", CALL_BENCH_SRC)
    print_source_block("配列合計", ARRAY_SUM_BENCH_SRC)
    print_source_block("定数畳み込み・配列", CONSTANT_FOLD_ARRAY_BENCH_SRC)
    print_source_block("インライン展開・配列", INLINE_ARRAY_BENCH_SRC)
    print_source_block("tryあり・例外なし", TRY_NO_EXCEPTION_BENCH_SRC)
    print_source_block("例外発生", EXCEPTION_BENCH_SRC)


def print_benchmark_results():
    specs = [
        ("BaseVM 関数呼び出し", CALL_BENCH_SRC, BaseVM),
        ("拡張VM 関数呼び出し", CALL_BENCH_SRC, VM),
        ("拡張VM 配列合計", ARRAY_SUM_BENCH_SRC, VM),
        ("拡張VM 定数畳み込み・配列", CONSTANT_FOLD_ARRAY_BENCH_SRC, VM),
        ("拡張VM インライン展開・配列", INLINE_ARRAY_BENCH_SRC, VM),
        ("拡張VM tryあり・例外なし", TRY_NO_EXCEPTION_BENCH_SRC, VM),
        ("拡張VM 例外発生", EXCEPTION_BENCH_SRC, VM),
    ]

    results = [
        (benchmark(label, src, vm_class), benchmark(label, src, vm_class, optimize=True))
        for label, src, vm_class in specs
    ]

    call_base = results[0][0]
    call_extended = results[1][0]
    try_no_exception = results[5][0]
    exception_extended = results[6][0]
    overhead = call_extended["min"] / call_base["min"]
    exception_cost = exception_extended["min"] / try_no_exception["min"]

    print("== ベンチマーク結果 ==")
    for no_opt, opt in results:
        time_ratio = opt["min"] / no_opt["min"]
        instruction_ratio = opt["instructions"] / no_opt["instructions"]
        instruction_delta = opt["instructions"] - no_opt["instructions"]
        print(f"{no_opt['label']}:")
        print(
            f"  最適化なし: min={no_opt['min']:.6f}s avg={no_opt['avg']:.6f}s "
            f"instructions={no_opt['instructions']}"
        )
        print(
            f"  最適化あり: min={opt['min']:.6f}s avg={opt['avg']:.6f}s "
            f"instructions={opt['instructions']}"
        )
        print(
            f"  あり/なし比: time={time_ratio:.2f}x "
            f"instructions={instruction_ratio:.2f}x delta={instruction_delta}"
        )
    print(f"通常実行での拡張VM/BaseVM比: {overhead:.2f}x")
    print(f"例外発生/例外なしtry比: {exception_cost:.2f}x")


if __name__ == "__main__":
    print_benchmark_programs()
    print_benchmark_results()

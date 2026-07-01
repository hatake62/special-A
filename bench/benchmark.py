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
    EXCEPTION_BENCH_SRC,
    TRY_NO_EXCEPTION_BENCH_SRC,
)


def benchmark(label, src, vm_class, repeat=5):
    functions = build(src)
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
    print_source_block("tryあり・例外なし", TRY_NO_EXCEPTION_BENCH_SRC)
    print_source_block("例外発生", EXCEPTION_BENCH_SRC)


def print_benchmark_results():
    results = [
        benchmark("BaseVM 関数呼び出し", CALL_BENCH_SRC, BaseVM),
        benchmark("拡張VM 関数呼び出し", CALL_BENCH_SRC, VM),
        benchmark("拡張VM 配列合計", ARRAY_SUM_BENCH_SRC, VM),
        benchmark("拡張VM tryあり・例外なし", TRY_NO_EXCEPTION_BENCH_SRC, VM),
        benchmark("拡張VM 例外発生", EXCEPTION_BENCH_SRC, VM),
    ]

    call_base, call_extended, _, try_no_exception, exception_extended = results
    overhead = call_extended["min"] / call_base["min"]
    exception_cost = exception_extended["min"] / try_no_exception["min"]

    print("== ベンチマーク結果 ==")
    for result in results:
        print(
            f"{result['label']}: "
            f"min={result['min']:.6f}s avg={result['avg']:.6f}s "
            f"instructions={result['instructions']}"
        )
    print(f"通常実行での拡張VM/BaseVM比: {overhead:.2f}x")
    print(f"例外発生/例外なしtry比: {exception_cost:.2f}x")


if __name__ == "__main__":
    print_benchmark_programs()
    print_benchmark_results()

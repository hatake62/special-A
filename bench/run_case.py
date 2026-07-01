import argparse
import contextlib
import io
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from bench.programs import CONSTANT_FOLD_ARRAY_BENCH_SRC  # noqa: E402
from src import VM, build  # noqa: E402


CASES = {
    "constant_fold_array": {
        "label": "拡張VM 定数畳み込み・配列",
        "src": CONSTANT_FOLD_ARRAY_BENCH_SRC,
        "vm_class": VM,
    }
}


def non_negative_float(value):
    seconds = float(value)
    if seconds < 0:
        raise argparse.ArgumentTypeError("--seconds must be greater than or equal to 0")
    return seconds


def positive_int(value):
    repeat = int(value)
    if repeat < 1:
        raise argparse.ArgumentTypeError("--repeat must be greater than or equal to 1")
    return repeat


def run_case(case_name, optimize=False, seconds=None, repeat=None):
    case = CASES[case_name]
    functions = build(case["src"], optimize=optimize)
    total_instruction_count = 0
    result = None
    run_count = 0

    start = time.perf_counter()
    if seconds is None:
        target_repeat = repeat if repeat is not None else 1
        for _ in range(target_repeat):
            vm = case["vm_class"](functions)
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result = vm.run()
            total_instruction_count += vm.instruction_count
            run_count += 1
        elapsed = time.perf_counter() - start
        mode = "repeat"
    else:
        mode = "seconds"
        while True:
            vm = case["vm_class"](functions)
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result = vm.run()
            total_instruction_count += vm.instruction_count
            run_count += 1

            elapsed = time.perf_counter() - start
            if elapsed >= seconds:
                break

    return {
        "case": case_name,
        "optimize": optimize,
        "mode": mode,
        "repeat": run_count,
        "elapsed_sec": elapsed,
        "instruction_count": total_instruction_count,
        "result": result,
    }


def print_json(payload):
    print(json.dumps(payload, ensure_ascii=False))


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="電力測定用に単一ベンチマークケースを実行する。"
    )
    parser.add_argument(
        "case",
        choices=sorted(CASES),
        help="実行するベンチマークケース名",
    )
    parser.add_argument(
        "--opt",
        action="store_true",
        help="定数畳み込み最適化を有効にする",
    )
    duration_group = parser.add_mutually_exclusive_group()
    duration_group.add_argument(
        "--seconds",
        type=non_negative_float,
        help="指定した秒数以上、同じベンチマークを繰り返し実行する",
    )
    duration_group.add_argument(
        "--repeat",
        type=positive_int,
        help="指定した回数、同じベンチマークを繰り返し実行する",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="最適化なし/ありを続けて実行し、出力結果の一致を表示する",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    if args.compare:
        no_opt = run_case(
            args.case, optimize=False, seconds=args.seconds, repeat=args.repeat
        )
        opt = run_case(args.case, optimize=True, seconds=args.seconds, repeat=args.repeat)
        result_match = no_opt["result"] == opt["result"]
        print_json(
            {
                "case": args.case,
                "result_match": result_match,
                "no_opt": no_opt,
                "opt": opt,
            }
        )
        return 0 if result_match else 1

    print_json(
        run_case(args.case, optimize=args.opt, seconds=args.seconds, repeat=args.repeat)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

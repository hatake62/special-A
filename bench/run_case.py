import argparse
import contextlib
import io
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


def run_case(case_name, optimize=False):
    case = CASES[case_name]
    functions = build(case["src"], optimize=optimize)
    vm = case["vm_class"](functions)
    stdout = io.StringIO()

    start = time.perf_counter()
    with contextlib.redirect_stdout(stdout):
        result = vm.run()
    elapsed = time.perf_counter() - start

    return {
        "case": case_name,
        "label": case["label"],
        "optimize": optimize,
        "elapsed": elapsed,
        "instruction_count": vm.instruction_count,
        "stdout": stdout.getvalue(),
        "result": result,
    }


def format_output_value(run):
    stdout = run["stdout"].strip()
    if stdout:
        return stdout
    return repr(run["result"])


def print_run(run):
    print(f"case: {run['case']} ({run['label']})")
    print(f"optimize: {'on' if run['optimize'] else 'off'}")
    print(f"elapsed: {run['elapsed']:.6f}s")
    print(f"instruction_count: {run['instruction_count']}")
    print(f"output: {format_output_value(run)}")


def print_comparison(no_opt, opt):
    no_opt_output = format_output_value(no_opt)
    opt_output = format_output_value(opt)
    same_output = no_opt_output == opt_output

    print("== comparison ==")
    print(f"case: {no_opt['case']} ({no_opt['label']})")
    print(f"output_match: {'yes' if same_output else 'no'}")
    print(f"no_opt_output: {no_opt_output}")
    print(f"opt_output: {opt_output}")
    print(f"no_opt_instruction_count: {no_opt['instruction_count']}")
    print(f"opt_instruction_count: {opt['instruction_count']}")
    print(
        "instruction_delta: "
        f"{opt['instruction_count'] - no_opt['instruction_count']}"
    )


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
    parser.add_argument(
        "--compare",
        action="store_true",
        help="最適化なし/ありを続けて実行し、出力結果の一致を表示する",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    if args.compare:
        no_opt = run_case(args.case, optimize=False)
        opt = run_case(args.case, optimize=True)
        print_run(no_opt)
        print()
        print_run(opt)
        print()
        print_comparison(no_opt, opt)
        return 0 if format_output_value(no_opt) == format_output_value(opt) else 1

    print_run(run_case(args.case, optimize=args.opt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

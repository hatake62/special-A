import io

import pytest

import main
from src import BaseVM, VM, VMError, build, run_src


def test_function_call_prints_result(capsys):
    src = """
def add(a, b):
    return a + b

print(add(10, 20))
"""
    run_src(src, VM)
    assert capsys.readouterr().out.strip() == "30"


def test_loop_and_function_call_runs_to_default_return():
    src = """
def add1(n):
    return n + 1

i = 0
total = 0
while i < 10:
    total = add1(total)
    i = i + 1
"""
    assert run_src(src, VM) == 0


def test_array_literal_and_index_access(capsys):
    src = """
arr = [1, 2, 3]
print(arr[0])
print(arr[1])
print(arr[2])
"""
    run_src(src, VM)
    assert capsys.readouterr().out.strip().splitlines() == ["1", "2", "3"]


def test_array_can_be_passed_to_function(capsys):
    src = """
def first(a):
    return a[0]

arr = [10, 20, 30]
print(first(arr))
"""
    run_src(src, VM)
    assert capsys.readouterr().out.strip() == "10"


def test_array_len(capsys):
    src = """
arr = [1, 2, 3, 4]
print(len(arr))
"""
    run_src(src, VM)
    assert capsys.readouterr().out.strip() == "4"


def test_empty_array_len(capsys):
    src = """
arr = []
print(len(arr))
"""
    run_src(src, VM)
    assert capsys.readouterr().out.strip() == "0"


def test_array_index_assignment(capsys):
    src = """
arr = [1, 2, 3]
arr[1] = 99
print(arr[1])
"""
    run_src(src, VM)
    assert capsys.readouterr().out.strip() == "99"


def test_array_update_and_expression_index_in_function(capsys):
    src = """
def pick(a, i):
    return a[i + 1]

arr = [3, 4, 5]
arr[2] = 9
print(pick(arr, 1))
"""
    run_src(src, VM)
    assert capsys.readouterr().out.strip() == "9"


def test_constant_folding_preserves_results_including_arrays(capsys):
    src = """
def pick(values):
    return values[0] + values[1] + values[2] + values[3]

arr = [1 + 2, 3 * 4, 10 - 1, 8 / 2]
print(pick(arr))
"""
    run_src(src, VM)
    no_opt_output = capsys.readouterr().out.strip()

    run_src(src, VM, optimize=True)
    opt_output = capsys.readouterr().out.strip()

    assert opt_output == no_opt_output == "28"


def test_constant_folding_reduces_arithmetic_instructions():
    src = "print((2 + 3) * (10 - 1))\n"

    no_opt_code = build(src)["main"]["code"]
    opt_code = build(src, optimize=True)["main"]["code"]

    assert ["add"] in no_opt_code
    assert ["mul"] in no_opt_code
    assert ["push", 45] in opt_code
    assert ["add"] not in opt_code
    assert ["mul"] not in opt_code


def test_function_inlining_preserves_output_with_arrays(capsys):
    src = """
def add_value(values, i):
    return values[i] + 1

arr = [3, 4, 5]
i = 0
total = 0
while i < 3:
    total = total + add_value(arr, i)
    i = i + 1
print(total)
"""
    run_src(src, VM)
    no_opt_output = capsys.readouterr().out.strip()

    run_src(src, VM, optimize=True)
    opt_output = capsys.readouterr().out.strip()

    assert opt_output == no_opt_output == "15"


def test_function_inlining_removes_simple_call_from_main():
    src = """
def add_value(values, i):
    return values[i] + 1

arr = [10]
print(add_value(arr, 0))
"""
    no_opt_code = build(src)["main"]["code"]
    opt_code = build(src, optimize=True)["main"]["code"]

    assert ["call", "add_value", 2] in no_opt_code
    assert ["call", "add_value", 2] not in opt_code
    assert ["call", "print", 1] in opt_code


def test_inlining_and_constant_folding_are_combined():
    src = """
def add_folded(n):
    return n + (2 * 3)

print(add_folded(4))
"""
    opt_code = build(src, optimize=True)["main"]["code"]

    assert ["call", "add_folded", 1] not in opt_code
    assert ["push", 10] in opt_code
    assert ["add"] not in opt_code
    assert ["mul"] not in opt_code


def test_inlining_skips_functions_with_control_flow_or_raise(capsys):
    src = """
def fail_if_zero(n):
    if n == 0:
        raise 1
    return n

try:
    print(fail_if_zero(0))
except:
    print(999)
"""
    opt_code = build(src, optimize=True)["main"]["code"]

    run_src(src, VM, optimize=True)

    assert ["call", "fail_if_zero", 1] in opt_code
    assert capsys.readouterr().out.strip() == "999"


def test_inlining_skips_recursive_return_expression():
    src = """
def loop(n):
    return loop(n)

print(loop(1))
"""
    opt_code = build(src, optimize=True)["main"]["code"]

    assert ["call", "loop", 1] in opt_code


def test_exception_is_caught(capsys):
    src = """
def fail():
    raise 1

try:
    print(fail())
except:
    print(999)
"""
    run_src(src, VM)
    assert capsys.readouterr().out.strip() == "999"


def test_exception_propagates_across_function_calls(capsys):
    src = """
def fail():
    raise 1

def wrapper():
    return fail()

try:
    print(wrapper())
except:
    print(777)
"""
    run_src(src, VM)
    assert capsys.readouterr().out.strip() == "777"


def test_uncaught_exception_raises_vm_error():
    with pytest.raises(VMError):
        run_src("raise 1", VM)


def test_base_vm_does_not_support_raise_instruction():
    with pytest.raises(ValueError):
        run_src("raise 1", BaseVM)


def test_vm_counts_executed_instructions():
    vm = VM(build("print(1)\n"))

    assert vm.instruction_count == 0
    vm.run()
    assert vm.instruction_count > 0


def test_main_runs_source_file(tmp_path, capsys):
    source = tmp_path / "program.src"
    source.write_text("print(123)\n", encoding="utf-8")

    assert main.main([str(source)]) == 0
    assert capsys.readouterr().out.strip() == "123"


def test_main_reads_source_from_stdin(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("print(456)\n"))

    assert main.main(["-"]) == 0
    assert capsys.readouterr().out.strip() == "456"


def test_main_enables_optimization_with_opt(tmp_path, capsys):
    source = tmp_path / "program.src"
    source.write_text("print(2 + 3)\n", encoding="utf-8")

    assert main.main(["--opt", str(source)]) == 0
    assert capsys.readouterr().out.strip() == "5"


def test_main_returns_error_status_for_missing_file(capsys):
    assert main.main(["missing.src"]) == 1
    assert "error:" in capsys.readouterr().err

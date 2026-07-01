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


def test_main_returns_error_status_for_missing_file(capsys):
    assert main.main(["missing.src"]) == 1
    assert "error:" in capsys.readouterr().err

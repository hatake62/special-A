import io

import pytest

import main
from src import BaseVM, VM, VMError, run_src


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

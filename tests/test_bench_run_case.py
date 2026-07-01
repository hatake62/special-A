import json

import pytest

from bench import run_case


def load_cli_json(capsys):
    return json.loads(capsys.readouterr().out)


def test_run_case_outputs_required_json_fields(capsys):
    assert run_case.main(["constant_fold_array", "--seconds", "0"]) == 0

    payload = load_cli_json(capsys)

    assert set(payload) == {
        "case",
        "optimize",
        "opt_mode",
        "mode",
        "repeat",
        "elapsed_sec",
        "instruction_count",
        "result",
    }
    assert payload["case"] == "constant_fold_array"
    assert payload["optimize"] is False
    assert payload["opt_mode"] == "none"
    assert payload["mode"] == "seconds"
    assert payload["repeat"] >= 1
    assert payload["elapsed_sec"] >= 0
    assert payload["instruction_count"] > 0
    assert payload["result"] == 0


def test_run_case_repeats_fixed_number_of_times(capsys):
    assert run_case.main(["constant_fold_array", "--repeat", "3"]) == 0

    payload = load_cli_json(capsys)

    assert payload["mode"] == "repeat"
    assert payload["repeat"] == 3
    assert payload["instruction_count"] > 0
    assert payload["result"] == 0


def test_run_case_enables_optimization_with_opt(capsys):
    assert run_case.main(["constant_fold_array", "--repeat", "2"]) == 0
    no_opt = load_cli_json(capsys)

    assert run_case.main(["constant_fold_array", "--opt", "--repeat", "2"]) == 0
    opt = load_cli_json(capsys)

    assert no_opt["optimize"] is False
    assert opt["optimize"] is True
    assert opt["opt_mode"] == "all"
    assert no_opt["repeat"] == opt["repeat"] == 2
    assert opt["result"] == no_opt["result"]
    assert opt["instruction_count"] < no_opt["instruction_count"]


def test_run_case_supports_inline_array_case(capsys):
    assert run_case.main(["inline_array", "--compare", "--repeat", "1"]) == 0

    payload = load_cli_json(capsys)

    assert payload["case"] == "inline_array"
    assert payload["result_match"] is True
    assert payload["opt"]["instruction_count"] < payload["no_opt"]["instruction_count"]


def test_run_case_compare_reports_matching_results(capsys):
    assert run_case.main(["constant_fold_array", "--compare", "--repeat", "2"]) == 0

    payload = load_cli_json(capsys)

    assert payload["case"] == "constant_fold_array"
    assert payload["result_match"] is True
    assert payload["no_opt"]["optimize"] is False
    assert payload["no_opt"]["opt_mode"] == "none"
    assert payload["opt"]["optimize"] is True
    assert payload["opt"]["opt_mode"] == "all"
    assert payload["no_opt"]["repeat"] == payload["opt"]["repeat"] == 2
    assert payload["no_opt"]["result"] == payload["opt"]["result"]


def test_run_case_supports_combined_array_optimization_modes(capsys):
    assert run_case.main(["combined_array", "--repeat", "1"]) == 0
    no_opt = load_cli_json(capsys)

    assert run_case.main(["combined_array", "--opt", "const", "--repeat", "1"]) == 0
    const_opt = load_cli_json(capsys)

    assert run_case.main(["combined_array", "--opt", "all", "--repeat", "1"]) == 0
    all_opt = load_cli_json(capsys)

    assert no_opt["opt_mode"] == "none"
    assert const_opt["opt_mode"] == "const"
    assert all_opt["opt_mode"] == "all"
    assert no_opt["result"] == const_opt["result"] == all_opt["result"]
    assert const_opt["instruction_count"] < no_opt["instruction_count"]
    assert all_opt["instruction_count"] < const_opt["instruction_count"]


def test_run_case_rejects_seconds_and_repeat_together():
    with pytest.raises(SystemExit):
        run_case.parse_args(["constant_fold_array", "--seconds", "0", "--repeat", "1"])

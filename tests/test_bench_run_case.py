import json

from bench import run_case


def load_cli_json(capsys):
    return json.loads(capsys.readouterr().out)


def test_run_case_outputs_required_json_fields(capsys):
    assert run_case.main(["constant_fold_array", "--seconds", "0"]) == 0

    payload = load_cli_json(capsys)

    assert set(payload) == {
        "case",
        "optimize",
        "elapsed_sec",
        "instruction_count",
        "result",
    }
    assert payload["case"] == "constant_fold_array"
    assert payload["optimize"] is False
    assert payload["elapsed_sec"] >= 0
    assert payload["instruction_count"] > 0
    assert payload["result"] == 0


def test_run_case_enables_optimization_with_opt(capsys):
    assert run_case.main(["constant_fold_array", "--seconds", "0"]) == 0
    no_opt = load_cli_json(capsys)

    assert run_case.main(["constant_fold_array", "--opt", "--seconds", "0"]) == 0
    opt = load_cli_json(capsys)

    assert no_opt["optimize"] is False
    assert opt["optimize"] is True
    assert opt["result"] == no_opt["result"]
    assert opt["instruction_count"] < no_opt["instruction_count"]


def test_run_case_compare_reports_matching_results(capsys):
    assert run_case.main(["constant_fold_array", "--compare", "--seconds", "0"]) == 0

    payload = load_cli_json(capsys)

    assert payload["case"] == "constant_fold_array"
    assert payload["result_match"] is True
    assert payload["no_opt"]["optimize"] is False
    assert payload["opt"]["optimize"] is True
    assert payload["no_opt"]["result"] == payload["opt"]["result"]

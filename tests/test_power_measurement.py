import json
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

from power import measure_special_a, queries


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_query_power_watt_averages_kepler_samples(monkeypatch):
    seen = {}

    def fake_urlopen(url, timeout):
        seen["url"] = url
        seen["timeout"] = timeout
        return FakeResponse(
            {
                "status": "success",
                "data": {
                    "result": [
                        {"values": [[1, "2.0"], [2, "4.0"], [3, "6.0"]]},
                    ]
                },
            }
        )

    monkeypatch.setattr(queries, "urlopen", fake_urlopen)

    power = queries.query_power_watt(
        "http://prometheus:9090",
        "special-a-noopt-abc",
        "default",
        10,
        20,
    )

    parsed = urlparse(seen["url"])
    params = parse_qs(parsed.query)
    assert power == 4.0
    assert seen["timeout"] == 30
    assert parsed.path == "/api/v1/query_range"
    assert params["start"] == ["10.0"]
    assert params["end"] == ["20.0"]
    assert "kepler_pod_cpu_watts" in params["query"][0]
    assert 'pod_name="special-a-noopt-abc"' in params["query"][0]
    assert 'container_namespace="default"' in params["query"][0]


def test_restart_deployment_runs_rollout_commands(monkeypatch):
    calls = []

    def fake_run_kubectl(args):
        calls.append(args)
        return ""

    monkeypatch.setattr(measure_special_a, "run_kubectl", fake_run_kubectl)

    measure_special_a.restart_deployment("bench", "special-a-noopt")

    assert calls == [
        ["rollout", "restart", "deployment/special-a-noopt", "-n", "bench"],
        ["rollout", "status", "deployment/special-a-noopt", "-n", "bench"],
    ]


def test_append_result_creates_csv_with_header(tmp_path):
    path = tmp_path / "power_results.csv"
    row = {field: field for field in measure_special_a.CSV_FIELDS}

    measure_special_a.append_result(path, row)
    measure_special_a.append_result(path, row)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0].split(",") == measure_special_a.CSV_FIELDS
    assert len(lines) == 3


def test_measure_records_energy_and_appends_csv(monkeypatch, tmp_path):
    calls = []
    started_at = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(
        measure_special_a,
        "restart_deployment",
        lambda namespace, deployment: calls.append(("restart", namespace, deployment)),
    )
    monkeypatch.setattr(
        measure_special_a,
        "deployment_selector",
        lambda namespace, deployment: "app=special-a-noopt",
    )
    monkeypatch.setattr(
        measure_special_a,
        "wait_for_running_pod",
        lambda namespace, selector: {
            "metadata": {
                "name": "special-a-noopt-abc",
                "creationTimestamp": "2026-01-01T00:00:00Z",
            },
            "status": {
                "containerStatuses": [
                    {"state": {"running": {"startedAt": started_at.isoformat()}}}
                ]
            },
        },
    )
    monkeypatch.setattr(
        measure_special_a,
        "query_power_watt",
        lambda prometheus_url, pod_name, namespace, start_time, end_time: 2.5,
    )
    monkeypatch.setattr(measure_special_a.time, "sleep", lambda seconds: None)

    results = tmp_path / "results.csv"
    args = measure_special_a.parse_args(
        [
            "--namespace",
            "bench",
            "--deployment",
            "special-a-noopt",
            "--prometheus-url",
            "http://prometheus:9090",
            "--seconds",
            "3",
            "--results",
            str(results),
        ]
    )

    row = measure_special_a.measure(args)

    assert calls == [("restart", "bench", "special-a-noopt")]
    assert row["pod"] == "special-a-noopt-abc"
    assert row["elapsed_sec"] == "3.000000"
    assert row["power_watt"] == "2.500000000"
    assert row["energy_joule"] == "7.500000000"
    assert results.exists()

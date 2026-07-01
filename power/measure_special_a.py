import argparse
import csv
import json
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from power.queries import query_power_watt


CSV_FIELDS = [
    "measured_at",
    "namespace",
    "deployment",
    "pod",
    "case",
    "optimize",
    "seconds",
    "start_time",
    "end_time",
    "elapsed_sec",
    "power_watt",
    "energy_joule",
]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="special-A の Kubernetes/Kepler 電力測定結果をCSVに保存する。"
    )
    parser.add_argument("--namespace", default="default", help="Kubernetes namespace")
    parser.add_argument("--deployment", required=True, help="再起動する Deployment 名")
    parser.add_argument(
        "--prometheus-url",
        required=True,
        help="Prometheus base URL, e.g. http://localhost:9090",
    )
    parser.add_argument("--opt", action="store_true", help="最適化ありの測定として記録する")
    parser.add_argument("--seconds", type=float, default=60.0, help="測定秒数")
    parser.add_argument(
        "--results",
        default="results/power_results.csv",
        help="追記するCSVファイル",
    )
    return parser.parse_args(argv)


def run_kubectl(args):
    completed = subprocess.run(
        ["kubectl", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def restart_deployment(namespace, deployment):
    target = f"deployment/{deployment}"
    run_kubectl(["rollout", "restart", target, "-n", namespace])
    run_kubectl(["rollout", "status", target, "-n", namespace])


def deployment_selector(namespace, deployment):
    raw = run_kubectl(["get", "deployment", deployment, "-n", namespace, "-o", "json"])
    payload = json.loads(raw)
    labels = payload.get("spec", {}).get("selector", {}).get("matchLabels", {})
    if not labels:
        raise RuntimeError(f"Deployment {deployment!r} has no matchLabels selector")
    return ",".join(f"{key}={value}" for key, value in sorted(labels.items()))


def parse_k8s_timestamp(value):
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def newest_running_pod(namespace, selector):
    raw = run_kubectl(["get", "pods", "-n", namespace, "-l", selector, "-o", "json"])
    pods = json.loads(raw).get("items", [])
    running = [
        pod
        for pod in pods
        if pod.get("status", {}).get("phase") == "Running"
        and pod.get("metadata", {}).get("creationTimestamp")
    ]
    if not running:
        return None

    return max(
        running,
        key=lambda pod: parse_k8s_timestamp(pod["metadata"]["creationTimestamp"]),
    )


def wait_for_running_pod(namespace, selector, timeout_sec=120):
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        pod = newest_running_pod(namespace, selector)
        if pod is not None:
            return pod
        time.sleep(1)
    raise TimeoutError(f"Timed out waiting for running pod with selector {selector!r}")


def pod_started_at(pod):
    for status in pod.get("status", {}).get("containerStatuses", []):
        running = status.get("state", {}).get("running")
        if running and running.get("startedAt"):
            return parse_k8s_timestamp(running["startedAt"])
    return parse_k8s_timestamp(pod["metadata"]["creationTimestamp"])


def append_result(path, row):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    needs_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        if needs_header:
            writer.writeheader()
        writer.writerow(row)


def measure(args):
    if args.seconds <= 0:
        raise ValueError("--seconds must be greater than 0")

    restart_deployment(args.namespace, args.deployment)
    selector = deployment_selector(args.namespace, args.deployment)
    pod = wait_for_running_pod(args.namespace, selector)
    pod_name = pod["metadata"]["name"]

    start_time = pod_started_at(pod)
    end_time = start_time + timedelta(seconds=args.seconds)
    now = datetime.now(timezone.utc)
    if now < end_time:
        time.sleep((end_time - now).total_seconds())

    power_watt = query_power_watt(
        args.prometheus_url,
        pod_name,
        args.namespace,
        start_time,
        end_time,
    )
    elapsed_sec = (end_time - start_time).total_seconds()
    energy_joule = elapsed_sec * power_watt

    row = {
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "namespace": args.namespace,
        "deployment": args.deployment,
        "pod": pod_name,
        "case": "constant_fold_array",
        "optimize": "true" if args.opt else "false",
        "seconds": f"{args.seconds:g}",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "elapsed_sec": f"{elapsed_sec:.6f}",
        "power_watt": f"{power_watt:.9f}",
        "energy_joule": f"{energy_joule:.9f}",
    }
    append_result(args.results, row)
    return row


def main(argv=None):
    args = parse_args(argv)
    row = measure(args)
    print(json.dumps(row, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

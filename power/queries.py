import json
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import urlopen


def _prometheus_timestamp(value):
    if isinstance(value, datetime):
        return value.timestamp()
    return float(value)


def _escape_label(value):
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def build_power_query(pod_name, namespace):
    pod_name = _escape_label(pod_name)
    namespace = _escape_label(namespace)
    selectors = [
        f'pod_name="{pod_name}",container_namespace="{namespace}"',
        f'pod_name="{pod_name}",namespace="{namespace}"',
        f'pod="{pod_name}",namespace="{namespace}"',
    ]
    return " or ".join(
        f"sum(kepler_pod_cpu_watts{{{selector}}})" for selector in selectors
    )


def query_power_watt(prometheus_url, pod_name, namespace, start_time, end_time, step="5s"):
    """Return average Kepler CPU power in watts for a pod over a time window."""

    start = _prometheus_timestamp(start_time)
    end = _prometheus_timestamp(end_time)
    if end <= start:
        raise ValueError("end_time must be after start_time")

    query = build_power_query(pod_name, namespace)
    params = urlencode(
        {
            "query": query,
            "start": start,
            "end": end,
            "step": step,
        }
    )
    url = f"{prometheus_url.rstrip('/')}/api/v1/query_range?{params}"

    with urlopen(url, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if payload.get("status") != "success":
        raise RuntimeError(f"Prometheus query failed: {payload}")

    values = []
    for series in payload.get("data", {}).get("result", []):
        for _, value in series.get("values", []):
            values.append(float(value))

    if not values:
        raise RuntimeError(
            "Prometheus returned no kepler_pod_cpu_watts samples "
            f"for pod={pod_name!r} namespace={namespace!r}"
        )

    return sum(values) / len(values)

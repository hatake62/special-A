# 消費電力の測定方法と実行方法

この資料では、special-A のベンチマークを Kubernetes 上で実行し、Kepler と Prometheus を使って消費電力を測定する手順をまとめる。

## 測定の考え方

消費電力の測定では、ベンチマークを Pod として実行し、その Pod の電力メトリクスを Kepler で取得する。Kepler が取得した値は Prometheus に保存されるため、Prometheus にクエリを投げて測定値を確認する。

主に使うメトリクスは次の値である。

```text
kepler_pod_cpu_watts
```

これは Pod 単位の CPU 消費電力を表す。単位は W、つまりワットである。

消費エネルギーは、平均消費電力と実行時間から計算する。

```text
消費エネルギー J = 平均消費電力 W * 実行時間 sec
```

平均消費電力だけを見ると、最適化後に値が少し上がる場合もある。しかし、実行時間が短くなれば、全体の消費エネルギーは下がることがある。そのため、比較では消費エネルギーを重視する。

## ベンチマークの実行方法

ベンチマークは `bench/run_case.py` で実行する。

ローカルで実行する例:

```bash
python bench/run_case.py constant_fold_array --repeat 100
python bench/run_case.py constant_fold_array --opt --repeat 100
```

`--repeat 100` は、ベンチマークプログラム全体を 100 回実行する指定である。例えば `inline_array` の中には `while i < 20000` のループがあるため、`--repeat 100` の場合は 20000 回ループするプログラムを 100 回実行する。

比較実行もできる。

```bash
python bench/run_case.py constant_fold_array --compare --repeat 100
python bench/run_case.py inline_array --compare --repeat 100
python bench/run_case.py combined_array --compare --repeat 100
```

`combined_array` では、最適化モードを指定できる。

```bash
python bench/run_case.py combined_array --repeat 100
python bench/run_case.py combined_array --opt const --repeat 100
python bench/run_case.py combined_array --opt all --repeat 100
```

それぞれの意味は次の通りである。

```text
--opt なし     最適化なし
--opt const    定数畳み込みのみ
--opt all      定数畳み込み + インライン展開
```

## コンテナの作成

Kubernetes 上で測定するため、ベンチマークを実行するコンテナイメージを作成する。

```bash
docker build -f Dockerfile.power -t special-a-power:latest .
```

クラスタがローカルイメージを直接参照できない場合は、レジストリに push する。

```bash
docker tag special-a-power:latest <registry>/special-a-power:latest
docker push <registry>/special-a-power:latest
```

ローカルクラスタを使う場合は、各ノードから `special-a-power:latest` を参照できる状態にしておく。

## Kubernetes マニフェストの役割

`k8s/` 以下の YAML ファイルは Kubernetes マニフェストである。マニフェストとは、Kubernetes に対して「この Pod を作って、このコンテナを実行してほしい」と伝える設定ファイルである。

例:

```bash
kubectl apply -f k8s/special-a-noopt.yaml
```

`-f` は file の指定で、読み込むマニフェストファイルを指定している。

主な YAML ファイルの役割は次の通りである。

| ファイル | 実行内容 |
| --- | --- |
| `k8s/special-a-noopt.yaml` | `constant_fold_array` を最適化なしで実行 |
| `k8s/special-a-opt.yaml` | `constant_fold_array` を最適化ありで実行 |
| `k8s/special-a-inline-noopt.yaml` | `inline_array` を最適化なしで実行 |
| `k8s/special-a-inline-opt.yaml` | `inline_array` を最適化ありで実行 |
| `k8s/special-a-combined-noopt.yaml` | `combined_array` を最適化なしで実行 |
| `k8s/special-a-combined-const.yaml` | `combined_array` を定数畳み込みのみで実行 |
| `k8s/special-a-combined-all.yaml` | `combined_array` を定数畳み込み + インライン展開で実行 |

YAML の中では、例えば次のようなコマンドを指定している。

```yaml
command: ["python"]
args:
  - bench/run_case.py
  - constant_fold_array
  - --repeat
  - "100"
```

これは次のコマンドをコンテナ内で実行するという意味である。

```bash
python bench/run_case.py constant_fold_array --repeat 100
```

## Kubernetes 上での実行

最適化なしと最適化ありを実行する。

```bash
kubectl apply -f k8s/special-a-noopt.yaml
kubectl apply -f k8s/special-a-opt.yaml
```

実行結果は Pod のログで確認する。

```bash
kubectl logs special-a-noopt
kubectl logs special-a-opt
```

再測定する場合は、完了した Pod を削除してから再度実行する。

```bash
kubectl delete pod special-a-noopt special-a-opt
kubectl apply -f k8s/special-a-noopt.yaml
kubectl apply -f k8s/special-a-opt.yaml
```

`combined_array` を測定する場合は次のように実行する。

```bash
kubectl apply -f k8s/special-a-combined-noopt.yaml
kubectl apply -f k8s/special-a-combined-const.yaml
kubectl apply -f k8s/special-a-combined-all.yaml
```

## Prometheus への接続

Prometheus が Kubernetes クラスタ内で動いている場合、ローカルからアクセスできるように port-forward する。

```bash
kubectl port-forward -n monitoring svc/prometheus 9090:9090
```

`-n monitoring` は、`monitoring` namespace にある Prometheus を対象にするという意味である。

`9090:9090` は、ローカル PC の 9090 番ポートを Kubernetes 内の Prometheus の 9090 番ポートにつなぐ指定である。

この状態で、ローカルから次の URL にアクセスできる。

```text
http://localhost:9090
```

## Prometheus で消費電力を確認する

Pod の直近 1 分間の平均消費電力を見る例:

```bash
curl -G "http://localhost:9090/api/v1/query" \
  --data-urlencode 'query=avg_over_time(kepler_pod_cpu_watts{pod_name="special-a-noopt",pod_namespace="default",zone="package"}[1m])' \
  | jq
```

このクエリは、`special-a-noopt` Pod の直近 1 分間の `kepler_pod_cpu_watts` の平均を取得している。

PromQL の部分は次の意味である。

```promql
avg_over_time(
  kepler_pod_cpu_watts{
    pod_name="special-a-noopt",
    pod_namespace="default",
    zone="package"
  }[1m]
)
```

| 部分 | 意味 |
| --- | --- |
| `kepler_pod_cpu_watts` | Kepler が出力する Pod 単位の CPU 消費電力 |
| `pod_name="special-a-noopt"` | 対象 Pod を指定 |
| `pod_namespace="default"` | 対象 namespace を指定 |
| `zone="package"` | CPU package 領域の値を指定 |
| `[1m]` | 直近 1 分間を対象にする |
| `avg_over_time(...)` | 指定期間の平均値を計算する |

最適化ありの Pod を見る場合は、Pod 名を変える。

```bash
curl -G "http://localhost:9090/api/v1/query" \
  --data-urlencode 'query=avg_over_time(kepler_pod_cpu_watts{pod_name="special-a-opt",pod_namespace="default",zone="package"}[1m])' \
  | jq
```

## 測定結果の記録

測定結果として記録する値は、主に次の項目である。

| 項目 | 内容 |
| --- | --- |
| ケース | `constant_fold_array`, `inline_array`, `combined_array` など |
| 最適化条件 | 最適化なし、定数畳み込みのみ、全最適化など |
| 実行時間 | `bench/run_case.py` の `elapsed_sec` |
| VM 命令数 | `bench/run_case.py` の `instruction_count` |
| 平均消費電力 | Prometheus から取得した平均 W |
| 消費エネルギー | `平均消費電力 W * 実行時間 sec` |

例えば、平均消費電力が `0.0000025 W`、実行時間が `60 sec` の場合:

```text
0.0000025 W * 60 sec = 0.00015 J
```

この `0.00015 J` が消費エネルギーである。

## 自動で CSV に保存する方法

`power/measure_special_a.py` を使うと、Prometheus から取得した平均消費電力と、計算した消費エネルギーを CSV に保存できる。

例:

```bash
python -m power.measure_special_a \
  --namespace default \
  --deployment special-a-noopt \
  --prometheus-url http://localhost:9090 \
  --seconds 60 \
  --results results/power_results.csv
```

最適化ありとして記録する場合:

```bash
python -m power.measure_special_a \
  --namespace default \
  --deployment special-a-opt \
  --prometheus-url http://localhost:9090 \
  --opt \
  --seconds 60 \
  --results results/power_results.csv
```

CSV には次の列が保存される。

```text
measured_at,namespace,deployment,pod,case,optimize,seconds,start_time,end_time,elapsed_sec,power_watt,energy_joule
```

注意点として、このスクリプトは Deployment を対象にしている。一方で、現在の `k8s/*.yaml` は Pod マニフェストである。Pod マニフェストを手動で実行して Prometheus を確認する方法と、Deployment を用意して `power/measure_special_a.py` で CSV 化する方法は別の実行方法として考える。

## 測定時の注意点

電力測定は実行環境の負荷に影響されるため、最適化なしと最適化ありはできるだけ同じ条件で測定する。

YAML では CPU とメモリの requests と limits を同じ値にしている。

```yaml
resources:
  requests:
    cpu: 500m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 256Mi
```

これにより、Pod ごとのリソース条件をそろえやすくしている。`cpu: 500m` は 0.5 CPU、`memory: 256Mi` は 256MiB を意味する。

比較では、絶対値そのものよりも、同じ環境で測定した相対的な差を見ることが重要である。

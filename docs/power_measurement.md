# Kubernetes/Kepler 電力測定用コンテナ

`Dockerfile.power` は Kepler で測定しやすいように、同じベンチマークを長時間実行するためのコンテナです。

## ビルド

```bash
docker build -f Dockerfile.power -t special-a-power:latest .
```

## ローカル実行

最適化なし:

```bash
docker run --rm special-a-power:latest
```

最適化あり:

```bash
docker run --rm -e OPT=1 special-a-power:latest
```

デフォルトでは次を実行します。

```bash
python bench/run_case.py constant_fold_array --seconds 60
```

`OPT=1` を指定した場合は次を実行します。

```bash
python bench/run_case.py constant_fold_array --opt --seconds 60
```

実行結果は JSON で標準出力に出ます。`result` が最適化なし/ありで同じことは、コンテナ外で次の比較コマンドでも確認できます。

```bash
python bench/run_case.py constant_fold_array --compare --seconds 60
```

## Kubernetes 実行例

クラスタから参照できるレジストリに push してから、Pod として起動します。

```bash
docker tag special-a-power:latest <registry>/special-a-power:latest
docker push <registry>/special-a-power:latest
```

ローカルクラスタでローカルイメージを使う場合は、`special-a-power:latest` を各ノードから参照できる状態にしてから適用します。マニフェストは `image: special-a-power:latest` と `imagePullPolicy: IfNotPresent` を使います。

最適化なしを起動:

```bash
kubectl apply -f k8s/special-a-noopt.yaml
```

最適化ありを起動:

```bash
kubectl apply -f k8s/special-a-opt.yaml
```

実行結果の JSON は Pod ログで確認します。

```bash
kubectl logs special-a-noopt
kubectl logs special-a-opt
```

同じ名前で再測定する場合は、完了した Pod を削除してから再度 apply します。

```bash
kubectl delete pod special-a-noopt special-a-opt
kubectl apply -f k8s/special-a-noopt.yaml
kubectl apply -f k8s/special-a-opt.yaml
```

最適化なしのマニフェスト:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: special-a-noopt
  labels:
    app: special-a-noopt
spec:
  restartPolicy: Never
  containers:
    - name: benchmark
      image: special-a-power:latest
```

最適化ありのマニフェスト:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: special-a-opt
  labels:
    app: special-a-opt
spec:
  restartPolicy: Never
  containers:
    - name: benchmark
      image: special-a-power:latest
      env:
        - name: OPT
          value: "1"
```

Kepler 側では `pod_name` や `app=special-a-noopt` / `app=special-a-opt` のラベルで、最適化なし/ありの Pod を分けて集計します。

## Prometheus からCSVへ保存

`power/measure_special_a.py` は Deployment を再起動し、新しく起動した Pod の実行時間帯について Prometheus から Kepler の `kepler_pod_cpu_watts` を取得します。取得した平均電力Wと実行時間からエネルギーJを計算し、CSVへ追記します。

このスクリプトは Deployment を対象にします。`--deployment` には、`constant_fold_array --seconds 60` を実行するコンテナを持つ Deployment 名を指定してください。

最適化なし:

```bash
python -m power.measure_special_a \
  --namespace default \
  --deployment special-a-noopt \
  --prometheus-url http://localhost:9090 \
  --seconds 60 \
  --results results/power_results.csv
```

最適化あり:

```bash
python -m power.measure_special_a \
  --namespace default \
  --deployment special-a-opt \
  --prometheus-url http://localhost:9090 \
  --opt \
  --seconds 60 \
  --results results/power_results.csv
```

CSV には次の列が出力されます。

```text
measured_at,namespace,deployment,pod,case,optimize,seconds,start_time,end_time,elapsed_sec,power_watt,energy_joule
```

`energy_joule` は `elapsed_sec * power_watt` で計算します。Prometheus の URL は、ポートフォワードしている場合は次のように指定できます。

```bash
kubectl port-forward -n monitoring svc/prometheus 9090:9090
```

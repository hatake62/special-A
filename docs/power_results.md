# 電力測定結果

`bench/run_case.py` で単一ベンチマークを実行し、電力測定結果を記録する。

## 実行コマンド

```bash
python bench/run_case.py constant_fold_array
python bench/run_case.py constant_fold_array --opt
python bench/run_case.py constant_fold_array --compare
```

## 結果記録表

| 測定日 | 環境 | ケース | 最適化 | 実行時間 | VM命令数 | 消費電力 | 消費エネルギー | 出力結果 | メモ |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
|  |  | constant_fold_array | なし |  |  |  |  |  |  |
|  |  | constant_fold_array | あり |  |  |  |  |  |  |

## 比較メモ

| 測定日 | ケース | 出力一致 | 最適化なし VM命令数 | 最適化あり VM命令数 | 命令削減数 | 電力差 | エネルギー差 | メモ |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
|  | constant_fold_array |  |  |  |  |  |  |  |

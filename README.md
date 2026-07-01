# special-A

`~/special/ch05` と同じ実行環境を再現するための最小構成です。

## Versions

- Ruby 3.0.2
- Python 3.10.12
- prism gem 1.9.0

## Setup

Ruby:

```sh
bundle config set path vendor/bundle
bundle install
```

Python:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

`requirements.txt` は空依存です。`ch05` の Python サンプルは標準ライブラリだけで動きます。

## Verify

```sh
ruby -e 'require "prism"; puts Prism::VERSION'
python --version
```

## Run

Demo:

```sh
python main.py
```

Production/source file:

```sh
python main.py path/to/program.src
```

Standard input:

```sh
python main.py - < path/to/program.src
```

By default, `main.py` uses the extended VM with `raise`/`except` support. To run
with the base VM:

```sh
python main.py --base-vm path/to/program.src
```

Array example:

```sh
python main.py examples/array.src
```

## Arrays

配列リテラル、添字アクセス、添字代入、`len` に対応しています。配列は関数に渡せるため、ループと組み合わせて集計処理も書けます。

```python
def first(values):
    return values[0]

numbers = [10, 20, 30]
numbers[1] = 25
print(first(numbers))
print(len(numbers))
```

スライスは未対応です。

## VM Instructions

- `build_array n`: スタック上の `n` 個の値から配列を作り、結果を積みます。
- `get_index`: スタックから配列と添字を取り出し、`array[index]` の値を積みます。
- `set_index`: スタックから配列、添字、値を取り出し、`array[index] = value` を実行して値を積みます。
- `len`: 組み込み関数として配列などの長さを返します。

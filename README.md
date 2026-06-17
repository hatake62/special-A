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

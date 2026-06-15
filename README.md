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

# コンパイラとVM実装の説明メモ

発表でコンパイラとVMの実装をコードで説明するときは、コードを上から全部読むのではなく、「ソースコードがVM命令になり、その命令をVMが1つずつ実行する」という流れを中心に説明する。

## 全体の流れ

この処理系は、Python風のコードをそのままPythonで実行しているのではなく、次の流れで実行している。

```text
ソースコード
  -> parser.py で簡易ASTへ変換
  -> optimizer.py で最適化
  -> compiler.py でVM命令列へ変換
  -> vm.py で実行
```

説明例:

> この処理系は、Python風のソースコードを自作VMで実行します。構文解析にはPython標準の `ast` を使っていますが、その後の簡易AST、VM命令、実行器はこのプロジェクトで実装しています。

## パーサの説明

`src/parser.py` では、Python標準のASTを、このVMで扱いやすい簡易ASTに変換している。

代表コード:

```python
if isinstance(node, ast.BinOp):
    return self.convert_binop(node)
```

`10 + 20` のような式は、内部では概念的に次の形になる。

```python
["add", ["int", 10], ["int", 20]]
```

説明例:

> まずPythonの構文を読み取り、VMで扱いやすいリスト形式の独自ASTへ変換します。たとえば足し算は `"add"`、整数は `"int"`、変数は `"var"` のように表します。

参照箇所:

- `src/parser.py`: `PythonToAst.convert`
- `src/parser.py`: `convert_binop`
- `src/parser.py`: `parse_program`

## コンパイラの説明

`src/compiler.py` の `compile_expr` が、簡易ASTをVM命令へ変換する中心部分である。

代表コード:

```python
elif tag in ("add", "sub", "mul", "div", "lt", "gt", "eq"):
    self.compile_expr(node[1])
    self.compile_expr(node[2])
    self.emit(tag)
```

このコードは、二項演算を次の順番でコンパイルしている。

1. 左辺をコンパイルする
2. 右辺をコンパイルする
3. 最後に演算命令を出す

例えば次の式があるとする。

```python
10 + 20
```

コンパイル後のVM命令は概念的に次のようになる。

```text
push 10
push 20
add
```

説明例:

> このVMはスタックマシンなので、演算を行う前に値をスタックへ積みます。`10 + 20` なら、まず10を積み、次に20を積み、最後に `add` 命令で2つを取り出して足します。

参照箇所:

- `src/compiler.py`: `compile_expr`
- `src/compiler.py`: `emit`
- `src/compiler.py`: `compile_program`

## 制御構文の説明

`if` や `while` は、条件分岐とジャンプ命令で実現している。

`while` の代表コード:

```python
def compile_while(self, node):
    _, cond, body = node
    top = len(self.code)
    self.compile_expr(cond)
    jf = self.emit_placeholder("jump_if_false")
    self.compile_block(body)
    self.emit("jump", top)
    self.patch(jf, len(self.code))
```

説明例:

> `while` 文では、まずループ先頭の命令位置を覚えます。次に条件式をコンパイルし、条件が偽ならループの外へ飛ぶ `jump_if_false` を置きます。ループ本体の最後では `jump` で先頭へ戻ります。ジャンプ先が後から決まる箇所は、仮の命令を置いて `patch` で番地を埋めています。

参照箇所:

- `src/compiler.py`: `compile_if`
- `src/compiler.py`: `compile_while`
- `src/compiler.py`: `emit_placeholder`
- `src/compiler.py`: `patch`

## VMの実行ループ

`src/vm.py` の `run` がVMの中心である。

代表コード:

```python
instr = frame.func["code"][frame.pc]
frame.pc += 1
self.instruction_count += 1
op = instr[0]
```

説明例:

> VMは現在のフレームから命令を1つ取り出し、`pc` を1つ進めます。その後、命令の種類に応じてスタックやローカル変数を操作します。ここで `instruction_count` を増やしているので、最適化によって実行命令数がどれだけ減ったかを測定できます。

参照箇所:

- `src/vm.py`: `BaseVM.run`
- `src/vm.py`: `instruction_count`

## スタックマシンの演算

二項演算は `execute_binary_op` で実行している。

代表コード:

```python
b, a = self.stack.pop(), self.stack.pop()

if op == "add":
    self.stack.append(a + b)
```

説明例:

> `add` 命令では、スタックから右辺と左辺を取り出し、足し算した結果をまたスタックに戻します。このように、VM命令は小さな操作に分解されています。

参照箇所:

- `src/vm.py`: `execute_binary_op`

## 関数呼び出し

関数呼び出しでは、引数をスタックから取り出し、ローカル変数領域を作って、新しいフレームを積む。

説明例:

> 関数呼び出しでは、スタック上の引数を取り出し、関数用のローカル変数配列を作ります。その後、新しいフレームを積むことで、呼び出し先の `pc`、ローカル変数、命令列を独立して管理します。`return` ではフレームを戻し、戻り値をスタックに戻します。

参照箇所:

- `src/vm.py`: `do_call`
- `src/vm.py`: `push_frame`
- `src/vm.py`: `do_return`
- `src/models.py`: `Frame`
- `src/models.py`: `BaseFrame`

## 例外処理

例外処理まで説明する場合は、コンパイル時に例外テーブルを作り、実行時にVMがハンドラを探す、という流れで説明する。

説明例:

> `try` 文はコンパイル時に例外テーブルへ登録します。実行中に `raise` や0除算が起きると、VMは現在のフレームから対応するハンドラを探します。見つかればハンドラの命令位置へ `pc` を移動し、見つからなければ呼び出し元のフレームへ戻りながら探索します。

参照箇所:

- `src/compiler.py`: `compile_try`
- `src/models.py`: `ExceptionEntry`
- `src/models.py`: `Frame.find_handler`
- `src/vm.py`: `VM.raise_exception`

## 発表でのまとめ文

> 実装で一番重要なのは、ソースコードを直接実行していない点です。まずPython風のコードを簡易ASTに変換し、次に `push`、`add`、`jump`、`call` のようなVM命令列に変換します。VMはその命令列を `pc` で1つずつ読み、スタックとフレームを操作して実行します。さらに命令実行時に `instruction_count` を数えているため、最適化によってどれだけ実行コストが下がったかを数値で確認できます。


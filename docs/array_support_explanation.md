# 配列対応の説明メモ

発表で配列への対応をコードで説明するときは、「配列リテラル」「配列参照」「配列更新」の3つに分けると説明しやすい。

## 全体の考え方

この処理系では、配列をPython風の構文で書ける。

```python
a = [1, 2, 3]
print(a[0])
a[1] = 10
print(len(a))
```

ただし、Pythonの配列構文をそのまま実行しているのではなく、次の流れでVM命令として実行している。

```text
[1, 2, 3]
  -> "array" という簡易AST
  -> build_array 命令
  -> VMがスタック上の値をまとめて配列にする
```

説明例:

> 配列は、ソースコード上ではPython風に `[1, 2, 3]`、`a[i]`、`a[i] = value` の形で書けます。ただしPythonで直接実行しているのではなく、パーサで独自ASTに変換し、コンパイラで配列用VM命令に変換し、VMがスタック上で処理しています。

## パーサ: 配列構文を簡易ASTに変換する

配列リテラルは、`src/parser.py` で `"array"` ノードに変換している。

代表コード:

```python
if isinstance(node, ast.List):
    return ["array", [self.convert(element) for element in node.elts]]
```

例えば次のコードがあるとする。

```python
a = [1, 2, 3]
```

配列部分は概念的に次の簡易ASTになる。

```python
["array", [["int", 1], ["int", 2], ["int", 3]]]
```

説明例:

> `[1, 2, 3]` は、パーサで `"array"` というノードに変換します。各要素も再帰的に変換するので、整数リテラルは `"int"` ノードになります。

参照箇所:

- `src/parser.py`: `PythonToAst.convert`

## パーサ: 配列参照を変換する

配列参照 `a[i]` は、`"index"` ノードに変換している。

代表コード:

```python
return ["index", self.convert(node.value), self.convert(node.slice)]
```

`a[i]` は概念的に次の簡易ASTになる。

```python
["index", ["var", "a"], ["var", "i"]]
```

説明例:

> 配列参照では、配列本体と添字をそれぞれ式として変換し、`"index"` ノードにまとめます。これにより、`a[0]` だけでなく、`a[i]` のような変数を使った添字にも対応できます。

参照箇所:

- `src/parser.py`: `convert_subscript`

## パーサ: 配列更新を変換する

配列への代入 `a[i] = value` は、通常の変数代入とは分けて `"set_index"` ノードに変換している。

代表コード:

```python
if isinstance(target, ast.Subscript):
    _, array, index = self.convert_subscript(target)
    return ["set_index", array, index, self.convert(node.value)]
```

説明例:

> 代入先が通常の変数なら `"assign"` にしますが、代入先が `a[i]` の形なら `"set_index"` に変換します。配列本体、添字、代入する値をそれぞれ保持して、あとでVM命令へ変換します。

参照箇所:

- `src/parser.py`: `convert_assign`

## コンパイラ: 配列リテラルをVM命令にする

`src/compiler.py` では、配列の各要素を順番にコンパイルし、最後に `build_array` 命令を出している。

代表コード:

```python
elif tag == "array":
    _, elements = node
    for element in elements:
        self.compile_expr(element)
    self.emit("build_array", len(elements))
```

`[1, 2, 3]` は概念的に次のVM命令になる。

```text
push 1
push 2
push 3
build_array 3
```

説明例:

> `[1, 2, 3]` の場合、まず `1`、`2`、`3` を順番にスタックへ積みます。そのあと `build_array 3` 命令で、スタック上の3つの値をまとめて1つの配列にします。

参照箇所:

- `src/compiler.py`: `compile_expr`

## コンパイラ: 配列参照をVM命令にする

配列参照は、配列本体と添字をスタックに積んでから `get_index` 命令を出す。

代表コード:

```python
elif tag == "index":
    self.compile_expr(node[1])
    self.compile_expr(node[2])
    self.emit("get_index")
```

`a[i]` は概念的に次のVM命令になる。

```text
get_local a
get_local i
get_index
```

説明例:

> `a[i]` では、まず配列本体をスタックに積み、次に添字を積みます。最後に `get_index` 命令で、配列から指定位置の値を取り出します。

参照箇所:

- `src/compiler.py`: `compile_expr`

## コンパイラ: 配列更新をVM命令にする

配列更新は、配列本体、添字、値をスタックに積んでから `set_index` 命令を出す。

代表コード:

```python
elif tag == "set_index":
    self.compile_expr(node[1])
    self.compile_expr(node[2])
    self.compile_expr(node[3])
    self.emit("set_index")
```

`a[i] = value` は概念的に次の順番で実行される。

```text
配列を積む
添字を積む
値を積む
set_index
```

説明例:

> 配列更新では、配列本体、添字、代入する値の順にスタックへ積みます。最後に `set_index` 命令を実行することで、VMが配列の指定位置を書き換えます。

参照箇所:

- `src/compiler.py`: `compile_stmt`

## VM: 配列を生成する

VM側では、`build_array` 命令を `execute_build_array` で実行している。

代表コード:

```python
values = self.stack[-count:]
del self.stack[-count:]
self.stack.append(values)
```

説明例:

> `build_array` は、スタックの末尾から指定個数分の値を取り出し、それらをPythonのリストとしてまとめます。そして、できた配列を1つの値としてスタックに戻します。

参照箇所:

- `src/vm.py`: `execute_build_array`

## VM: 配列から値を取り出す

配列参照は、`get_index` 命令を `execute_get_index` で実行している。

代表コード:

```python
index = self.stack.pop()
array = self.stack.pop()
self.stack.append(array[index])
```

説明例:

> `get_index` では、まず添字をスタックから取り出し、次に配列本体を取り出します。その後、`array[index]` の結果をスタックに戻します。

参照箇所:

- `src/vm.py`: `execute_get_index`

## VM: 配列を書き換える

配列更新は、`set_index` 命令を `execute_set_index` で実行している。

代表コード:

```python
value = self.stack.pop()
index = self.stack.pop()
array = self.stack.pop()
array[index] = value
self.stack.append(value)
```

説明例:

> `set_index` では、値、添字、配列の順にスタックから取り出し、配列の要素を書き換えます。最後に代入した値をスタックへ戻します。

参照箇所:

- `src/vm.py`: `execute_set_index`

## `len` への対応

配列の長さ取得は、VMの組み込み関数 `len` として実装している。

代表コード:

```python
if name == "len":
    if argc != 1:
        raise ValueError("引数の個数が違います: len")
    value = self.stack.pop()
    self.stack.append(len(value))
    return
```

説明例:

> `len(a)` は通常の関数呼び出しと同じ形でコンパイルされます。VMで関数名が `len` だった場合は組み込み関数として扱い、スタックから配列を取り出して長さを計算し、結果をスタックへ戻します。

参照箇所:

- `src/vm.py`: `do_call`

## 発表でのまとめ文

> 配列対応では、`[1, 2, 3]` をそのまま実行するのではなく、まず `"array"` という独自ASTに変換します。コンパイル時には各要素をスタックに積む命令を出し、最後に `build_array` 命令で1つの配列にまとめます。配列参照 `a[i]` は、配列と添字をスタックに積んで `get_index`、配列更新 `a[i] = value` は、配列・添字・値を積んで `set_index` で実行します。このように、配列もスタックVMの命令として扱えるように実装しました。


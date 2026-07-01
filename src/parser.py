import ast


BIN_OPS = {
    ast.Add: "add",
    ast.Sub: "sub",
    ast.Mult: "mul",
    ast.Div: "div",
}

COMPARE_OPS = {
    ast.Lt: "lt",
    ast.Gt: "gt",
    ast.Eq: "eq",
}


class PythonToAst:
    """Pythonの一部構文を、このVM用の簡易ASTに変換する。"""

    def __init__(self, src):
        self.tree = ast.parse(src)

    def parse_program(self):
        main = []
        defs = []

        for stmt in self.statements(self.tree.body):
            if stmt[0] == "def":
                _, name, params, body = stmt
                defs.append([name, params, body])
            else:
                main.append(stmt)

        return {"defs": defs, "main": main}

    def statements(self, nodes):
        return [self.convert(node) for node in nodes]

    def convert(self, node):
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return ["int", node.value]

        if isinstance(node, ast.Name):
            return ["var", node.id]

        if isinstance(node, ast.List):
            return ["array", [self.convert(element) for element in node.elts]]

        if isinstance(node, ast.Subscript):
            return self.convert_subscript(node)

        if isinstance(node, ast.Assign):
            return self.convert_assign(node)

        if isinstance(node, ast.FunctionDef):
            return ["def", node.name, self.parameters(node.args), self.statements(node.body)]

        if isinstance(node, ast.If):
            return [
                "if",
                self.convert(node.test),
                self.statements(node.body),
                self.statements(node.orelse),
            ]

        if isinstance(node, ast.While):
            return ["while", self.convert(node.test), self.statements(node.body)]

        if isinstance(node, ast.Try):
            return self.convert_try(node)

        if isinstance(node, ast.Raise):
            if node.exc is None or node.cause is not None:
                raise ValueError("raise は値を1つ指定してください")
            return ["raise", self.convert(node.exc)]

        if isinstance(node, ast.Return):
            if node.value is None:
                raise ValueError("return は値を1つ指定してください")
            return ["return", self.convert(node.value)]

        if isinstance(node, ast.Expr):
            return self.convert(node.value)

        if isinstance(node, ast.BinOp):
            return self.convert_binop(node)

        if isinstance(node, ast.Compare):
            return self.convert_compare(node)

        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("通常の関数呼び出しだけ対応しています")
            return ["call", node.func.id, [self.convert(arg) for arg in node.args]]

        raise ValueError(f"未対応の Python AST ノード: {node.__class__.__name__}")

    def convert_assign(self, node):
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            raise ValueError("代入先は通常の変数だけ対応しています")
        return ["assign", node.targets[0].id, self.convert(node.value)]

    def convert_subscript(self, node):
        if isinstance(node.slice, ast.Slice):
            raise ValueError("スライスは未対応です")
        return ["index", self.convert(node.value), self.convert(node.slice)]

    def convert_try(self, node):
        if node.orelse or node.finalbody:
            raise ValueError("try の else/finally は未対応です")
        if len(node.handlers) != 1:
            raise ValueError("except は1つだけ対応しています")

        handler = node.handlers[0]
        if handler.type is not None or handler.name is not None:
            raise ValueError("except の型指定と変数束縛は未対応です")

        return ["try", self.statements(node.body), self.statements(handler.body)]

    def convert_binop(self, node):
        for op_type, name in BIN_OPS.items():
            if isinstance(node.op, op_type):
                return [name, self.convert(node.left), self.convert(node.right)]
        raise ValueError(f"未対応の二項演算子: {node.op.__class__.__name__}")

    def convert_compare(self, node):
        if len(node.ops) != 1 or len(node.comparators) != 1:
            raise ValueError("比較演算子の連鎖は未対応です")
        for op_type, name in COMPARE_OPS.items():
            if isinstance(node.ops[0], op_type):
                return [name, self.convert(node.left), self.convert(node.comparators[0])]
        raise ValueError(f"未対応の比較演算子: {node.ops[0].__class__.__name__}")

    def parameters(self, node):
        if (
            node.posonlyargs
            or node.vararg
            or node.kwonlyargs
            or node.kw_defaults
            or node.kwarg
            or node.defaults
        ):
            raise ValueError("通常の必須引数だけ対応しています")

        return [param.arg for param in node.args]


def parse_program(src):
    return PythonToAst(src).parse_program()

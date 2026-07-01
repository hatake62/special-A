ARITHMETIC_OPS = {
    "add": lambda a, b: a + b,
    "sub": lambda a, b: a - b,
    "mul": lambda a, b: a * b,
    "div": lambda a, b: a // b,
}


def fold_constants(program):
    return {
        "defs": [
            [name, params, fold_stmt_list(body)] for name, params, body in program["defs"]
        ],
        "main": fold_stmt_list(program["main"]),
    }


def fold_stmt_list(statements):
    return [fold_stmt(stmt) for stmt in statements]


def fold_stmt(node):
    tag = node[0]

    if tag == "assign":
        return ["assign", node[1], fold_expr(node[2])]
    if tag == "set_index":
        return [
            "set_index",
            fold_expr(node[1]),
            fold_expr(node[2]),
            fold_expr(node[3]),
        ]
    if tag == "return":
        return ["return", fold_expr(node[1])]
    if tag == "raise":
        return ["raise", fold_expr(node[1])]
    if tag == "try":
        return ["try", fold_stmt_list(node[1]), fold_stmt_list(node[2])]
    if tag == "if":
        return ["if", fold_expr(node[1]), fold_stmt_list(node[2]), fold_stmt_list(node[3])]
    if tag == "while":
        return ["while", fold_expr(node[1]), fold_stmt_list(node[2])]

    return fold_expr(node)


def fold_expr(node):
    tag = node[0]

    if tag in ("int", "var"):
        return node
    if tag == "array":
        return ["array", [fold_expr(element) for element in node[1]]]
    if tag == "index":
        return ["index", fold_expr(node[1]), fold_expr(node[2])]
    if tag == "call":
        return ["call", node[1], [fold_expr(arg) for arg in node[2]]]
    if tag in ("add", "sub", "mul", "div", "lt", "gt", "eq"):
        left = fold_expr(node[1])
        right = fold_expr(node[2])
        if tag in ARITHMETIC_OPS and left[0] == "int" and right[0] == "int":
            if tag == "div" and right[1] == 0:
                return [tag, left, right]
            return ["int", ARITHMETIC_OPS[tag](left[1], right[1])]
        return [tag, left, right]

    raise ValueError(f"未知の式: {node}")

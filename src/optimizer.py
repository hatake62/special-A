ARITHMETIC_OPS = {
    "add": lambda a, b: a + b,
    "sub": lambda a, b: a - b,
    "mul": lambda a, b: a * b,
    "div": lambda a, b: a // b,
}


def optimize_program(program):
    program = fold_constants(program)
    program = inline_functions(program)
    return fold_constants(program)


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


def inline_functions(program):
    inlineable = collect_inlineable_functions(program["defs"])
    return {
        "defs": [
            [name, params, inline_stmt_list(body, inlineable)]
            for name, params, body in program["defs"]
        ],
        "main": inline_stmt_list(program["main"], inlineable),
    }


def collect_inlineable_functions(defs):
    functions = {}
    for name, params, body in defs:
        if is_inlineable_function(body):
            return_expr = body[0][1]
            functions[name] = (params, return_expr)
    return functions


def is_inlineable_function(body):
    if len(body) != 1 or body[0][0] != "return":
        return False

    return_expr = body[0][1]
    if contains_any_call(return_expr):
        return False

    return True


def inline_stmt_list(statements, inlineable):
    return [inline_stmt(stmt, inlineable) for stmt in statements]


def inline_stmt(node, inlineable):
    tag = node[0]

    if tag == "assign":
        return ["assign", node[1], inline_expr(node[2], inlineable)]
    if tag == "set_index":
        return [
            "set_index",
            inline_expr(node[1], inlineable),
            inline_expr(node[2], inlineable),
            inline_expr(node[3], inlineable),
        ]
    if tag == "return":
        return ["return", inline_expr(node[1], inlineable)]
    if tag == "raise":
        return ["raise", inline_expr(node[1], inlineable)]
    if tag == "try":
        return [
            "try",
            inline_stmt_list(node[1], inlineable),
            inline_stmt_list(node[2], inlineable),
        ]
    if tag == "if":
        return [
            "if",
            inline_expr(node[1], inlineable),
            inline_stmt_list(node[2], inlineable),
            inline_stmt_list(node[3], inlineable),
        ]
    if tag == "while":
        return [
            "while",
            inline_expr(node[1], inlineable),
            inline_stmt_list(node[2], inlineable),
        ]

    return inline_expr(node, inlineable)


def inline_expr(node, inlineable):
    tag = node[0]

    if tag in ("int", "var"):
        return node
    if tag == "array":
        return ["array", [inline_expr(element, inlineable) for element in node[1]]]
    if tag == "index":
        return [
            "index",
            inline_expr(node[1], inlineable),
            inline_expr(node[2], inlineable),
        ]
    if tag == "call":
        name = node[1]
        args = [inline_expr(arg, inlineable) for arg in node[2]]
        if name in inlineable:
            params, return_expr = inlineable[name]
            if len(params) == len(args):
                replacements = dict(zip(params, args))
                return inline_expr(substitute_expr(return_expr, replacements), inlineable)
        return ["call", name, args]
    if tag in ("add", "sub", "mul", "div", "lt", "gt", "eq"):
        return [tag, inline_expr(node[1], inlineable), inline_expr(node[2], inlineable)]

    raise ValueError(f"未知の式: {node}")


def substitute_expr(node, replacements):
    tag = node[0]

    if tag == "var" and node[1] in replacements:
        return clone_expr(replacements[node[1]])
    if tag in ("int", "var"):
        return node[:]
    if tag == "array":
        return ["array", [substitute_expr(element, replacements) for element in node[1]]]
    if tag == "index":
        return [
            "index",
            substitute_expr(node[1], replacements),
            substitute_expr(node[2], replacements),
        ]
    if tag == "call":
        return ["call", node[1], [substitute_expr(arg, replacements) for arg in node[2]]]
    if tag in ("add", "sub", "mul", "div", "lt", "gt", "eq"):
        return [
            tag,
            substitute_expr(node[1], replacements),
            substitute_expr(node[2], replacements),
        ]

    raise ValueError(f"未知の式: {node}")


def clone_expr(node):
    return substitute_expr(node, {})


def contains_any_call(node):
    tag = node[0]

    if tag == "call":
        return True
    if tag == "array":
        return any(contains_any_call(element) for element in node[1])
    if tag == "index":
        return contains_any_call(node[1]) or contains_any_call(node[2])
    if tag in ("add", "sub", "mul", "div", "lt", "gt", "eq"):
        return contains_any_call(node[1]) or contains_any_call(node[2])
    if tag in ("int", "var"):
        return False

    raise ValueError(f"未知の式: {node}")

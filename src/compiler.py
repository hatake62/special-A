from .models import ExceptionEntry
from .parser import parse_program


class Compiler:
    def __init__(self):
        self.code = []
        self.locals = []
        self.exception_table = []
        self.stack_depth = 0

    @property
    def nlocals(self):
        return len(self.locals)

    def emit(self, *instr):
        self.code.append(list(instr))
        self.update_stack_depth(instr)

    def update_stack_depth(self, instr):
        op = instr[0]
        if op in ("push", "get_local"):
            self.stack_depth += 1
        elif op == "pop":
            self.stack_depth -= 1
        elif op in ("add", "sub", "mul", "div", "lt", "gt", "eq"):
            self.stack_depth -= 1
        elif op == "set_local":
            pass
        elif op == "call":
            self.stack_depth -= instr[2]
            self.stack_depth += 1
        elif op in ("ret", "raise"):
            self.stack_depth -= 1

        if self.stack_depth < 0:
            raise ValueError("コンパイラ内部エラー: スタック深さが負になりました")

    def compile_expr(self, node):
        tag = node[0]

        if tag == "int":
            self.emit("push", node[1])
        elif tag == "var":
            self.emit("get_local", self.local_index(node[1]))
        elif tag in ("add", "sub", "mul", "div", "lt", "gt", "eq"):
            self.compile_expr(node[1])
            self.compile_expr(node[2])
            self.emit(tag)
        elif tag == "call":
            _, name, args = node
            for arg in args:
                self.compile_expr(arg)
            self.emit("call", name, len(args))
        else:
            raise ValueError(f"未知の式: {node}")

    def compile_stmt(self, node):
        tag = node[0]

        if tag == "assign":
            self.compile_expr(node[2])
            self.emit("set_local", self.local_index(node[1]))
        elif tag == "return":
            self.compile_expr(node[1])
            self.emit("ret")
        elif tag == "raise":
            self.compile_expr(node[1])
            self.emit("raise")
        elif tag == "try":
            self.compile_try(node)
        elif tag == "if":
            self.compile_if(node)
        elif tag == "while":
            self.compile_while(node)
        else:
            self.compile_expr(node)
            self.emit("pop")

    def compile_if(self, node):
        _, cond, then_body, else_body = node
        self.compile_expr(cond)
        jf = self.emit_placeholder("jump_if_false")
        self.compile_block(then_body)
        jend = self.emit_placeholder("jump")
        self.patch(jf, len(self.code))
        self.compile_block(else_body or [])
        self.patch(jend, len(self.code))

    def compile_while(self, node):
        _, cond, body = node
        top = len(self.code)
        self.compile_expr(cond)
        jf = self.emit_placeholder("jump_if_false")
        self.compile_block(body)
        self.emit("jump", top)
        self.patch(jf, len(self.code))

    def compile_try(self, node):
        _, body, handler_body = node
        start_pc = len(self.code)
        start_sp = self.stack_depth

        self.compile_block(body)

        leave = self.emit_placeholder("jump")
        end_pc = len(self.code)
        handler_pc = len(self.code)

        # ハンドラ開始時にはVMが例外値を1つ積む。
        self.stack_depth = start_sp + 1
        self.emit("pop")
        self.compile_block(handler_body)

        self.patch(leave, len(self.code))
        self.stack_depth = start_sp
        self.exception_table.append(
            ExceptionEntry(start_pc, end_pc, handler_pc, start_sp, "rescue")
        )

    def compile_block(self, body):
        for stmt in body:
            self.compile_stmt(stmt)

    def local_index(self, name):
        if name not in self.locals:
            self.locals.append(name)
        return self.locals.index(name)

    def emit_placeholder(self, op):
        self.code.append([op, None])
        return len(self.code) - 1

    def patch(self, index, addr):
        self.code[index][1] = addr


def compile_function(params, body):
    compiler = Compiler()
    for param in params:
        compiler.local_index(param)
    compiler.compile_block(body)
    compiler.emit("push", 0)
    compiler.emit("ret")
    return {
        "code": compiler.code,
        "exception_table": compiler.exception_table,
        "nparams": len(params),
        "nlocals": compiler.nlocals,
    }


def compile_program(program):
    functions = {}
    for name, params, body in program["defs"]:
        functions[name] = compile_function(params, body)
    functions["main"] = compile_function([], program["main"])
    return functions


def build(src):
    return compile_program(parse_program(src))

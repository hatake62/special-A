from .compiler import build
from .models import BaseFrame, Frame


class VMError(Exception):
    def __init__(self, value):
        self.value = value
        super().__init__(value)


class BaseVM:
    frame_class = BaseFrame

    def __init__(self, functions):
        self.functions = functions
        self.stack = []
        self.frames = []
        self.instruction_count = 0

    def run(self):
        self.do_call("main", 0)

        while True:
            frame = self.frames[-1]
            instr = frame.func["code"][frame.pc]
            frame.pc += 1
            self.instruction_count += 1
            op = instr[0]

            if op == "push":
                self.stack.append(instr[1])
            elif op == "pop":
                if self.stack:
                    self.stack.pop()
            elif op in ("add", "sub", "mul", "div", "lt", "gt", "eq"):
                self.execute_binary_op(op)
            elif op == "build_array":
                self.execute_build_array(instr[1])
            elif op == "get_index":
                self.execute_get_index()
            elif op == "set_index":
                self.execute_set_index()
            elif op == "get_local":
                self.stack.append(frame.locals[instr[1]])
            elif op == "set_local":
                frame.locals[instr[1]] = self.stack[-1]
            elif op == "jump":
                frame.pc = instr[1]
            elif op == "jump_if_false":
                if self.stack.pop() == 0:
                    frame.pc = instr[1]
            elif op == "call":
                self.do_call(instr[1], instr[2])
            elif op == "ret":
                self.do_return()
                if not self.frames:
                    return self.stack.pop()
            else:
                self.handle_unknown_instruction(instr)

    def execute_binary_op(self, op):
        b, a = self.stack.pop(), self.stack.pop()

        if op == "add":
            self.stack.append(a + b)
        elif op == "sub":
            self.stack.append(a - b)
        elif op == "mul":
            self.stack.append(a * b)
        elif op == "div":
            self.stack.append(a // b)
        elif op == "lt":
            self.stack.append(1 if a < b else 0)
        elif op == "gt":
            self.stack.append(1 if a > b else 0)
        elif op == "eq":
            self.stack.append(1 if a == b else 0)

    def execute_build_array(self, count):
        if count:
            values = self.stack[-count:]
            del self.stack[-count:]
        else:
            values = []
        self.stack.append(values)

    def execute_get_index(self):
        index = self.stack.pop()
        array = self.stack.pop()
        self.stack.append(array[index])

    def execute_set_index(self):
        value = self.stack.pop()
        index = self.stack.pop()
        array = self.stack.pop()
        array[index] = value
        self.stack.append(value)

    def handle_unknown_instruction(self, instr):
        raise ValueError(f"未知の命令: {instr}")

    def do_call(self, name, argc):
        if name == "print":
            value = self.stack.pop()
            print(value)
            self.stack.append(value)
            return

        if name == "len":
            if argc != 1:
                raise ValueError("引数の個数が違います: len")
            value = self.stack.pop()
            self.stack.append(len(value))
            return

        if name not in self.functions:
            raise ValueError(f"未定義の関数: {name}")

        func = self.functions[name]
        if func["nparams"] != argc:
            raise ValueError(f"引数の個数が違います: {name}")

        if argc:
            args = self.stack[-argc:]
            del self.stack[-argc:]
        else:
            args = []

        locals_ = [0] * func["nlocals"]
        for i, value in enumerate(args):
            locals_[i] = value

        self.push_frame(func, locals_)

    def push_frame(self, func, locals_):
        self.frames.append(self.frame_class(func, 0, locals_))

    def do_return(self):
        retval = self.stack.pop()
        self.frames.pop()
        self.stack.append(retval)


class VM(BaseVM):
    """try/except と raise を追加した拡張VM。"""

    frame_class = Frame

    def execute_binary_op(self, op):
        if op == "div":
            b, a = self.stack.pop(), self.stack.pop()
            if b == 0:
                self.raise_exception("divided by 0")
            else:
                self.stack.append(a // b)
            return

        super().execute_binary_op(op)

    def handle_unknown_instruction(self, instr):
        if instr[0] == "raise":
            self.raise_exception(self.stack.pop())
            return
        super().handle_unknown_instruction(instr)

    def push_frame(self, func, locals_):
        self.frames.append(Frame(func, 0, locals_, len(self.stack)))

    def do_return(self):
        retval = self.stack.pop()
        frame = self.frames.pop()
        del self.stack[frame.stack_base :]
        self.stack.append(retval)

    def raise_exception(self, value):
        while self.frames:
            frame = self.frames[-1]
            entry = frame.find_handler("rescue")
            if entry:
                del self.stack[frame.stack_base + entry.sp :]
                self.stack.append(value)
                frame.pc = entry.handler_pc
                return

            del self.stack[frame.stack_base :]
            self.frames.pop()

        raise VMError(value)


def run_src(src, vm_class=VM, optimize=False):
    return vm_class(build(src, optimize=optimize)).run()

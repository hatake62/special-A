from dataclasses import dataclass


@dataclass
class ExceptionEntry:
    start_pc: int
    end_pc: int
    handler_pc: int
    sp: int
    type: str


@dataclass
class Frame:
    func: dict
    pc: int
    locals: list
    stack_base: int

    def find_handler(self, exception_type):
        # 実行ループでは命令取得直後にpcを進めるので、直前の命令位置で検索する。
        current_pc = self.pc - 1
        for entry in self.func["exception_table"]:
            if (
                entry.start_pc <= current_pc < entry.end_pc
                and entry.type == exception_type
            ):
                return entry
        return None


@dataclass
class BaseFrame:
    func: dict
    pc: int
    locals: list

"""List creation, indexed loads and stores, and foreach over lists (LST-01…LST-04, EXP-08)."""

from pathlib import Path

from src.codegen.ir import OpCode, OperandKind
from src.semantic.types import FLOAT, INTEGER, ArrayType

CPS = Path(__file__).resolve().parents[1] / "cps"


def find(code, opcode):
    return [item for item in code if item.opcode is opcode]


def test_empty_and_non_empty_literals_store_elements_in_order(generate_tac):
    """LST-01: list_new with the literal's length, then one list_set per element."""
    lowered = generate_tac("let vacia = [];\nlet xs: integer[] = [10, 20, 30];\n")
    code = lowered.unit()
    empty, full = find(code, OpCode.LIST_NEW)
    assert (empty.arg1.value, full.arg1.value) == (0, 3)
    assert full.result.type == ArrayType(INTEGER)
    stores = find(code, OpCode.LIST_SET)
    assert [(s.arg1, s.arg2.value, s.result.value) for s in stores] == [
        (full.result, 0, 10), (full.result, 1, 20), (full.result, 2, 30),
    ]
    assert "    list_set t1, 1, 20" in lowered.text


def test_indexed_reads_from_a_real_program(generate_tac):
    """LST-02 with tests/cps/validos/LST-02-indice-entero.cps."""
    source = (CPS / "validos" / "LST-02-indice-entero.cps").read_text(encoding="utf8")
    code = generate_tac(source).unit()
    reads = find(code, OpCode.LIST_GET)
    assert [(r.arg1.value.symbol.name, r.arg2.value) for r in reads] == [
        ("valores", 0), ("valores", 2),
    ]
    assert all(r.result.kind is OperandKind.TEMPORARY and r.result.type == INTEGER for r in reads)


def test_indexed_store_uses_list_set(generate_tac):
    """LST-03 and EXP-08: a[i] = v is never a copy into the list variable."""
    lowered = generate_tac("let xs: integer[] = [1, 2];\nlet i: integer = 1;\nxs[i] = 5;\n")
    code = lowered.unit()
    store = find(code, OpCode.LIST_SET)[-1]
    assert store.arg1.value.symbol.name == "xs"
    assert store.arg2.value.symbol.name == "i" and store.result.value == 5
    copies = [c for c in find(code, OpCode.COPY) if c.result.kind is OperandKind.SYMBOL]
    assert [c.result.value.symbol.name for c in copies] == ["xs", "i"]


def test_store_expression_yields_the_assigned_value(generate_tac):
    code = generate_tac("let xs: integer[] = [1];\nlet y: integer = (xs[0] = 7);\n").unit()
    store = find(code, OpCode.LIST_SET)[-1]
    copy = find(code, OpCode.COPY)[-1]
    assert store.result.value == 7 and copy.arg1.value == 7
    assert code.index(store) < code.index(copy)


def test_nested_indexing_loads_the_row_then_stores_the_element(generate_tac):
    code = generate_tac(
        "let m: integer[][] = [[1, 2], [3, 4]];\nm[1][0] = m[0][1];\n"
    ).unit()
    tail = code[-8:]
    row = next(item for item in tail if item.opcode is OpCode.LIST_GET and item.arg2.value == 1)
    store = find(tail, OpCode.LIST_SET)[0]
    assert store.arg1 == row.result and store.arg2.value == 0
    loads = find(tail, OpCode.LIST_GET)
    assert store.result == loads[-1].result


def test_integer_elements_of_a_float_list_are_widened(generate_tac):
    code = generate_tac("let fs: float[] = [1, 2.5];\n").unit()
    first, second = find(code, OpCode.LIST_SET)
    assert first.result.value == 1.0 and first.result.type == FLOAT
    assert second.result.value == 2.5


def test_foreach_over_a_list_literal(generate_tac):
    """LST-04: the literal is built once, measured once and read by index."""
    lowered = generate_tac("foreach (n in [4, 5]) {\n  print(n);\n}\n")
    code = lowered.unit()
    (created,) = find(code, OpCode.LIST_NEW)
    (length,) = find(code, OpCode.LIST_LEN)
    (read,) = find(code, OpCode.LIST_GET)
    assert length.arg1 == created.result == read.arg1
    assert read.result.value.symbol.name == "n"


def test_list_base_is_captured_before_an_index_with_side_effects(generate_tac):
    """Left-to-right: xs is read before f() can replace it."""
    code = generate_tac(
        "let xs: integer[] = [1, 2];\n"
        "function f(): integer {\n  xs = [9];\n  return 0;\n}\n"
        "let v: integer = xs[f()];\n"
    ).unit()
    call = next(item for item in code if item.opcode is OpCode.CALL)
    snapshot = code[code.index(call) - 1]
    assert snapshot.opcode is OpCode.COPY and snapshot.arg1.value.symbol.name == "xs"
    (read,) = find(code, OpCode.LIST_GET)
    assert read.arg1 == snapshot.result and read.arg2 == call.result

"""Sizes, alignment, offsets, labels and class layouts (SYM-01..04, CLS-01, CLS-06)."""

import pytest

from src.codegen.layout import (
    ClassLayout,
    DuplicateLabelError,
    LabelRegistry,
    LayoutBuilder,
    LayoutError,
    Region,
    StorageClass,
    SymbolLayout,
    SymbolLayoutTable,
    align_up,
    check_no_overlap,
    find_overlap,
    layout_of,
)
from src.semantic.diagnostics import SourceLocation
from src.semantic.symbol_table import Symbol, SymbolKind
from src.semantic.types import (
    BOOLEAN,
    FLOAT,
    INTEGER,
    NULL,
    STRING,
    UNKNOWN,
    ArrayType,
    ClassType,
    FunctionType,
)

LOC = SourceLocation(1, 1)


def sym(name, type_=INTEGER, kind=SymbolKind.VARIABLE):
    return Symbol(name, kind, type_, True, LOC)


# -- sizes and alignment (SYM-02) ------------------------------------------------


@pytest.mark.parametrize(
    "type_,size,alignment",
    [
        (BOOLEAN, 1, 1),
        (INTEGER, 4, 4),
        (FLOAT, 8, 8),
        (STRING, 8, 8),
        (ArrayType(INTEGER), 8, 8),
        (ClassType("C"), 8, 8),
        (FunctionType((), INTEGER), 8, 8),
        (UNKNOWN, 8, 8),
        (NULL, 8, 8),
    ],
)
def test_every_type_has_the_documented_size_and_alignment(type_, size, alignment):
    layout = layout_of(type_)
    assert (layout.size, layout.alignment) == (size, alignment)


def test_align_up_is_ceiling_to_a_multiple():
    assert [align_up(v, 4) for v in (0, 1, 4, 5, 7, 8)] == [0, 4, 4, 8, 8, 8]
    assert align_up(9, 8) == 16
    with pytest.raises(LayoutError):
        align_up(1, 0)


@pytest.mark.parametrize("size,alignment", [(0, 4), (-4, 4), (4, 0), (4, 3)])
def test_zero_size_or_bad_alignment_is_rejected(size, alignment):
    with pytest.raises(LayoutError):
        LayoutBuilder("area").allocate("x", size, alignment)


# -- sequential allocation and overlap (SYM-03) ---------------------------------


def test_builder_aligns_each_allocation_and_never_overlaps():
    builder = LayoutBuilder("frame")
    offsets = [
        builder.allocate_type("flag", BOOLEAN)[0],
        builder.allocate_type("count", INTEGER)[0],
        builder.allocate_type("ratio", FLOAT)[0],
        builder.allocate_type("other", INTEGER)[0],
    ]
    assert offsets == [0, 4, 8, 16]
    assert builder.cursor == 20
    assert builder.total_size() == 24
    builder.validate()


def test_two_locals_get_different_offsets():
    builder = LayoutBuilder("frame")
    first = builder.allocate_type("a", INTEGER)[0]
    second = builder.allocate_type("a2", INTEGER)[0]
    assert first != second


def test_overlap_detection_names_both_regions():
    regions = [Region("a", 0, 8), Region("b", 4, 4)]
    assert find_overlap(regions) == (regions[0], regions[1])
    with pytest.raises(LayoutError, match="overlap in frame f: a .* and b"):
        check_no_overlap(regions, "frame f")
    assert find_overlap([Region("a", 0, 4), Region("b", 4, 4)]) is None


# -- SymbolLayout invariants -----------------------------------------------------


def test_symbol_layout_rejects_misaligned_offsets_and_bad_storage():
    x = sym("x")
    with pytest.raises(LayoutError, match="not aligned"):
        SymbolLayout(x, StorageClass.LOCAL, 4, 4, offset=2)
    with pytest.raises(LayoutError, match="unknown storage"):
        SymbolLayout(x, "heap", 4, 4, offset=0)  # type: ignore[arg-type]
    with pytest.raises(LayoutError):
        SymbolLayout(x, StorageClass.LOCAL, 0, 4, offset=0)
    with pytest.raises(LayoutError, match="neither an offset nor a label"):
        SymbolLayout(x, StorageClass.STATIC, 4, 4)
    with pytest.raises(LayoutError, match="environment offset"):
        SymbolLayout(x, StorageClass.CAPTURED, 4, 4, offset=0, captured=True)


def test_address_retains_the_symbol_by_identity():
    x = sym("x")
    layout = SymbolLayout(x, StorageClass.LOCAL, 4, 4, offset=36, frame="fn_f")
    address = layout.address()
    assert address.symbol is x
    assert (address.storage, address.offset, address.scope) == ("local", 36, "fn_f")
    static = SymbolLayout(x, StorageClass.STATIC, 4, 4, offset=0).address()
    assert static.scope is None and static.storage == "static"


# -- SymbolLayoutTable -----------------------------------------------------------


def test_table_finds_layouts_by_identity_not_by_equal_value():
    a, b = sym("x"), sym("x")
    assert a == b and a is not b
    table = SymbolLayoutTable(
        [
            SymbolLayout(a, StorageClass.STATIC, 4, 4, offset=0),
            SymbolLayout(b, StorageClass.STATIC, 4, 4, offset=4),
        ]
    )
    assert table.layout_for(a).offset == 0
    assert table.layout_for(b).offset == 4
    assert a in table and len(table) == 2
    with pytest.raises(LookupError):
        table.layout_for(sym("x"))


def test_table_rejects_overlap_in_one_frame_but_not_across_frames():
    x, y = sym("x"), sym("y")
    clash = [
        SymbolLayout(x, StorageClass.LOCAL, 4, 4, offset=0, frame="f"),
        SymbolLayout(y, StorageClass.LOCAL, 4, 4, offset=0, frame="f"),
    ]
    with pytest.raises(LayoutError, match="overlap in frame f"):
        SymbolLayoutTable(clash)
    SymbolLayoutTable(
        [
            SymbolLayout(x, StorageClass.LOCAL, 4, 4, offset=0, frame="f"),
            SymbolLayout(y, StorageClass.LOCAL, 4, 4, offset=0, frame="g"),
        ]
    )


def test_table_rejects_a_symbol_laid_out_twice_and_duplicate_labels():
    x = sym("x")
    layout = SymbolLayout(x, StorageClass.STATIC, 4, 4, offset=0)
    with pytest.raises(LayoutError, match="laid out twice"):
        SymbolLayoutTable([layout, layout])
    f, g = sym("f", kind=SymbolKind.FUNCTION), sym("g", kind=SymbolKind.FUNCTION)
    with pytest.raises(DuplicateLabelError):
        SymbolLayoutTable(
            [
                SymbolLayout(f, StorageClass.STATIC, 8, 8, label="fn"),
                SymbolLayout(g, StorageClass.STATIC, 8, 8, label="fn"),
            ]
        )


# -- labels (SYM-04) -------------------------------------------------------------


def test_label_registry_claims_once_and_derives_unique_names():
    registry = LabelRegistry()
    assert registry.claim("fn_a") == "fn_a"
    with pytest.raises(DuplicateLabelError):
        registry.claim("fn_a")
    assert registry.unique("fn_a") == "fn_a_2"
    assert registry.unique("fn_a") == "fn_a_3"
    assert "fn_a_2" in registry and len(registry) == 3
    with pytest.raises(LayoutError):
        registry.claim("")


# -- class layouts ----------------------------------------------------------------


def test_class_layout_rejects_overlapping_fields():
    a, b = sym("a", kind=SymbolKind.FIELD), sym("b", kind=SymbolKind.FIELD)
    fields = (
        SymbolLayout(a, StorageClass.FIELD, 4, 4, offset=0, frame="C"),
        SymbolLayout(b, StorageClass.FIELD, 4, 4, offset=0, frame="C"),
    )
    with pytest.raises(LayoutError, match="overlap in class C"):
        ClassLayout(sym("C", ClassType("C"), SymbolKind.CLASS), "C", 8, 8, fields)


# -- real programs ---------------------------------------------------------------

PROGRAM = """
class Base { let a: integer; let b: float; }
class Hija : Base {
  let c: boolean;
  function m(): integer { return this.a; }
}
function f(p: integer, q: float): integer {
  let l: integer = p;
  let z: boolean = true;
  return l;
}
let g: integer = 1;
const h: float = 2.5;
"""


def test_fields_are_aligned_and_base_fields_precede_derived_ones(compile_facts):
    _, facts = compile_facts(PROGRAM)
    classes = facts.layouts.classes
    base, hija = classes["Base"], classes["Hija"]

    assert [(f.name, f.offset) for f in base.fields] == [("a", 0), ("b", 8)]
    assert base.size == 16
    assert [(f.name, f.offset) for f in hija.all_fields] == [("a", 0), ("b", 8), ("c", 16)]
    assert [f.name for f in hija.fields] == ["c"]
    assert hija.size == 24 and hija.alignment == 8
    assert hija.field_offset("a") == base.field_offset("a")
    assert hija.method_label("m") == "Hija.m"
    assert hija.constructor_label == "Hija.constructor" and not hija.explicit_constructor
    assert hija.superclass is base
    with pytest.raises(LookupError):
        hija.field_offset("missing")
    with pytest.raises(LookupError):
        base.method_label("m")


def test_empty_class_still_reserves_one_word(compile_facts):
    _, facts = compile_facts("class Vacia { }\nlet v = new Vacia();\n")
    assert facts.layouts.classes["Vacia"].size == 8


def test_static_variables_are_aligned_and_do_not_overlap(compile_facts):
    _, facts = compile_facts(PROGRAM)
    table = facts.layouts.symbols
    statics = {l.name: l for l in table.by_storage(StorageClass.STATIC) if l.label is None}
    assert (statics["g"].offset, statics["g"].size) == (0, 4)
    assert (statics["h"].offset, statics["h"].size) == (8, 8)
    assert table.static_size == 16


def test_shadowing_yields_distinct_storage(compile_facts):
    source = (
        "let n: integer = 1;\n"
        "function f(): integer { let n: integer = 2; { let n: integer = 3; } return n; }\n"
    )
    _, facts = compile_facts(source)
    rows = [r for r in facts.layouts.symbols.rows() if r["name"] == "n"]
    assert len(rows) == 3
    frame_offsets = [r["offset"] for r in rows if r["frame"] == "fn_f"]
    assert len(set(frame_offsets)) == 2
    assert {r["storage"] for r in rows} == {"static", "local"}


def test_all_storage_classes_appear_in_the_extended_table(compile_facts):
    source = """
    class K { let campo: integer; }
    let global: integer = 1;
    function exterior(p: integer): integer {
      let capturada: integer = p;
      let libre: integer = 0;
      function interior(): integer { return capturada; }
      return interior();
    }
    """
    _, facts = compile_facts(source)
    storages = {row["storage"] for row in facts.layouts.symbols.rows()}
    assert {"static", "parameter", "local", "field", "captured"} <= storages


def test_every_symbol_has_size_alignment_and_a_location_in_memory_or_code(compile_facts):
    _, facts = compile_facts(PROGRAM)
    for row in facts.layouts.symbols.rows():
        assert row["size"] > 0 and row["alignment"] > 0
        assert row["offset"] is not None or row["label"] is not None
        if row["offset"] is not None:
            assert row["offset"] % row["alignment"] == 0


def test_labels_are_unique_and_deterministic(compile_facts):
    source = """
    class A { function go(): integer { return 1; } function back(): integer { return 2; } }
    function uno(): integer { function dentro(): integer { return 1; } return dentro(); }
    function dos(): integer { function dentro(): integer { return 2; } return dentro(); }
    """
    run, first = compile_facts(source)
    labels = first.layouts.symbols.labels()
    assert len(labels) == len(set(labels))
    assert {"A", "A.go", "A.back", "fn_uno", "fn_dos", "fn_uno.dentro", "fn_dos.dentro"} <= set(labels)

    from src.codegen.activation import build_runtime_layouts

    again = build_runtime_layouts(
        run.semantic_result.symbol_table, run.semantic_result.annotations
    )
    assert again.symbols.labels() == labels

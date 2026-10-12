"""Activation records, environments and captures (FUN-02, FUN-08, FUN-09, RUN-*, TMP-05)."""

from dataclasses import replace

import pytest

from src.codegen.activation import (
    HEADER_FIELDS,
    ActivationRecordBuilder,
    ActivationRecordLayout,
    EnvironmentLayout,
    EnvironmentSlot,
    FrameSlot,
    FrameSlotKind,
)
from src.codegen.ir import IRProcedure, IRProgram, Operand, OperandKind
from src.codegen.layout import LayoutError
from src.semantic.diagnostics import SourceLocation
from src.semantic.symbol_table import Symbol, SymbolKind
from src.semantic.types import BOOLEAN, FLOAT, INTEGER, ClassType

LOC = SourceLocation(1, 1)


def sym(name, type_=INTEGER, kind=SymbolKind.VARIABLE):
    return Symbol(name, kind, type_, True, LOC)


def header_frame():
    builder = ActivationRecordBuilder("fn_f", "f", 1)
    builder.reserve_header()
    return builder


# -- builder ordering and header -------------------------------------------------


def test_header_has_the_four_mandatory_fields_in_order():
    frame = header_frame().build()
    assert tuple(slot.name for slot in frame.header) == HEADER_FIELDS
    assert [slot.offset for slot in frame.header] == [0, 8, 16, 24]
    assert all(slot.size == 8 for slot in frame.header)
    assert frame.size == 32 and frame.size % frame.alignment == 0


def test_control_link_and_access_link_are_distinct_slots():
    frame = header_frame().build()
    control, access = frame.slot("control_link"), frame.slot("access_link")
    assert control.offset != access.offset
    assert frame.slot("return_address").offset != frame.slot("return_value").offset


def test_builder_reserves_in_order_and_aligns_every_slot():
    builder = header_frame()
    this = builder.reserve_hidden("this", ClassType("C"))
    first = builder.reserve_parameter(sym("p", BOOLEAN))
    second = builder.reserve_parameter(sym("q", FLOAT))
    local = builder.reserve_local(sym("l", INTEGER))
    frame = builder.build()

    assert this.hidden and this.offset == 32
    assert (first.offset, second.offset, local.offset) == (40, 48, 56)
    assert frame.size == 64
    assert [s.name for s in frame.hidden_parameters] == ["this"]
    assert [s.name for s in frame.parameters] == ["p", "q"]
    assert [s.name for s in frame.locals] == ["l"]
    assert all(slot.offset % slot.alignment == 0 for slot in frame.slots)


def test_builder_rejects_out_of_order_reservations():
    builder = ActivationRecordBuilder("fn_f", "f", 1)
    with pytest.raises(LayoutError, match="header first"):
        builder.reserve_parameter(sym("p"))
    builder.reserve_header()
    with pytest.raises(LayoutError, match="already reserved"):
        builder.reserve_header()
    builder.reserve_local(sym("l"))
    with pytest.raises(LayoutError, match="cannot reserve parameter after local"):
        builder.reserve_parameter(sym("p"))
    with pytest.raises(LayoutError, match="cannot reserve hidden after local"):
        builder.reserve_hidden("env")


def test_builder_cannot_build_without_a_header_or_reserve_after_building():
    with pytest.raises(LayoutError, match="header was never reserved"):
        ActivationRecordBuilder("fn_f", "f", 1).build()
    builder = header_frame()
    builder.build()
    with pytest.raises(LayoutError, match="already finalized"):
        builder.reserve_local(sym("late"))


def test_shadowed_names_get_their_own_slot_and_symbol_layout():
    builder = header_frame()
    outer, inner = sym("n"), sym("n")
    a = builder.reserve_local(outer)
    b = builder.reserve_local(inner)
    frame = builder.build()
    assert a.offset != b.offset
    assert [slot.name for slot in frame.locals] == ["n", "n#2"]
    assert frame.slot("n").symbol is outer and frame.slot("n#2").symbol is inner


def test_captured_locals_use_captured_slots_and_storage():
    builder = header_frame()
    layout = builder.reserve_local(sym("x"), captured=True, env_offset=0)
    frame = builder.build()
    assert layout.storage.value == "captured" and layout.captured
    assert frame.slot("x").kind is FrameSlotKind.CAPTURED


# -- structural validation (FUN-09 negative cases) -------------------------------


def test_layout_without_a_complete_header_is_rejected():
    slots = (FrameSlot("return_address", FrameSlotKind.HEADER, 0, 8, 8),)
    with pytest.raises(LayoutError, match="header must contain"):
        ActivationRecordLayout("fn", "f", 1, slots, 8)


def test_overlapping_or_misaligned_slots_are_rejected():
    frame = header_frame().build()
    with pytest.raises(LayoutError, match="overlap in frame fn_f"):
        replace(frame, slots=frame.slots + (FrameSlot("x", FrameSlotKind.LOCAL, 24, 8, 8),))
    with pytest.raises(LayoutError, match="not aligned"):
        FrameSlot("y", FrameSlotKind.LOCAL, 33, 4, 4)
    with pytest.raises(LayoutError, match="duplicate slot names"):
        replace(
            frame,
            slots=frame.slots + (FrameSlot("return_value", FrameSlotKind.LOCAL, 32, 8, 8),),
            size=40,
        )
    with pytest.raises(LayoutError, match="does not cover"):
        replace(frame, slots=frame.slots + (FrameSlot("z", FrameSlotKind.LOCAL, 32, 8, 8),))


# -- temporaries (RUN-04, TMP-05) -------------------------------------------------


def test_with_temporaries_reserves_exactly_the_peak_aligned_and_inside_the_frame():
    builder = header_frame()
    builder.reserve_local(sym("l", BOOLEAN))
    frame = builder.build().with_temporaries(3)

    assert [s.name for s in frame.temporaries] == ["t0", "t1", "t2"]
    assert [s.offset for s in frame.temporaries] == [40, 48, 56]
    assert frame.temporary_capacity == 3
    assert frame.size == 64
    frame.require_temporaries(3)


def test_changing_the_peak_replaces_the_previous_temporaries():
    frame = header_frame().build().with_temporaries(4).with_temporaries(1)
    assert frame.temporary_capacity == 1 and frame.size == 40
    assert header_frame().build().with_temporaries(0).temporary_capacity == 0


def test_fewer_slots_than_the_peak_fail_the_layout_check():
    frame = header_frame().build().with_temporaries(1)
    with pytest.raises(LayoutError, match="1 temporary slots for a peak of 2"):
        frame.require_temporaries(2)
    with pytest.raises(LayoutError):
        frame.with_temporaries(-1)


def test_builder_can_reserve_temporaries_directly():
    builder = header_frame()
    builder.reserve_local(sym("l"))
    builder.reserve_temporaries(2)
    frame = builder.build()
    assert [s.name for s in frame.temporaries] == ["t0", "t1"]
    with pytest.raises(LayoutError):
        header_frame().reserve_temporaries(-1)


def test_ir_peak_active_decides_the_temporary_slots(compile_facts):
    source = "function f(a: integer, b: integer): integer { return a + b * 2; }\n"
    _, facts = compile_facts(source)
    layouts = facts.layouts
    label = Operand(OperandKind.LABEL, "fn_f")
    program = IRProgram(procedures=(IRProcedure(label, (), (), temporary_peak=2),))

    final = layouts.finalize_temporaries(program, global_peak=1)
    assert final.frame_by_label("fn_f").temporary_capacity == 2
    assert final.global_frame.temporary_capacity == 1
    assert layouts.frame_by_label("fn_f").temporary_capacity == 0  # original untouched
    with pytest.raises(LookupError):
        layouts.with_temporary_peaks({"fn_missing": 1})


# -- environments ------------------------------------------------------------------


def test_environment_slots_and_access_link_must_not_overlap():
    x = sym("x")
    EnvironmentLayout("fn_f", (EnvironmentSlot(x, 0, 4, 4),), 8, 16)
    with pytest.raises(LayoutError, match="overlap in environment of fn_f"):
        EnvironmentLayout("fn_f", (EnvironmentSlot(x, 4, 8, 8),), 8, 16)
    with pytest.raises(LayoutError):
        EnvironmentLayout("fn_f", (EnvironmentSlot(x, 0, 4, 4),), 8, 12)
    with pytest.raises(LookupError):
        EnvironmentLayout("fn_f", (), 0, 8).offset_of(x)


# -- real programs -----------------------------------------------------------------


def test_function_frame_lists_parameters_locals_and_total_size(compile_facts):
    source = """
    function f(p: integer, q: float): integer {
      let l: integer = p;
      let z: boolean = true;
      return l;
    }
    """
    _, facts = compile_facts(source)
    frame = next(f for f in facts.layouts.frames if f.label == "fn_f")
    assert [(s.name, s.offset) for s in frame.parameters] == [("p", 32), ("q", 40)]
    assert [(s.name, s.offset) for s in frame.locals] == [("l", 48), ("z", 52)]
    assert frame.size == 56 and frame.level == 1
    assert not frame.captures and not frame.needs_env and frame.environment is None


def test_frames_of_different_functions_do_not_contaminate_each_other(compile_facts):
    source = """
    function uno(n: integer): integer { let a: integer = n; return a; }
    function dos(n: float): float { return n; }
    """
    _, facts = compile_facts(source)
    uno, dos = facts.layouts.frames
    assert [s.name for s in uno.locals] == ["a"] and not dos.locals
    assert uno.slot("n").type == INTEGER and dos.slot("n").type == FLOAT
    assert uno.slot("n").symbol is not dos.slot("n").symbol


def test_method_frame_starts_with_a_hidden_this(compile_facts):
    source = """
    class P {
      let x: integer;
      function dobla(k: integer): integer { return this.x * k; }
    }
    """
    _, facts = compile_facts(source)
    frame = facts.layouts.frame_by_label("P.dobla")
    assert [s.name for s in frame.hidden_parameters] == ["this"]
    assert frame.slot("this").type == ClassType("P")
    assert frame.slot("this").offset == 32 and frame.slot("k").offset == 40


def test_simple_capture_uses_the_env_parameter_at_depth_zero(compile_facts):
    source = """
    function exterior(): integer {
      let base: integer = 10;
      function interior(): integer { return base + 1; }
      return interior();
    }
    """
    _, facts = compile_facts(source)
    exterior = facts.layouts.frame_by_label("fn_exterior")
    interior = facts.layouts.frame_by_label("fn_exterior.interior")

    assert interior.needs_env and [s.name for s in interior.hidden_parameters] == ["env"]
    (capture,) = interior.captures
    assert (capture.symbol.name, capture.depth, capture.env_offset) == ("base", 0, 0)
    assert capture.owner_frame == "fn_exterior"
    assert not exterior.needs_env
    assert exterior.environment.offset_of(capture.symbol) == 0
    assert exterior.environment.size == 16 and exterior.environment.parent_offset == 8
    assert exterior.slot("base").kind is FrameSlotKind.CAPTURED


def test_two_level_capture_follows_one_access_link(compile_facts):
    source = """
    function a(): integer {
      let x: integer = 1;
      function b(): integer {
        let y: integer = 2;
        function c(): integer { return x + y; }
        return c();
      }
      return b();
    }
    """
    _, facts = compile_facts(source)
    frames = {f.label: f for f in facts.layouts.frames}
    c = frames["fn_a.b.c"]
    depths = {capture.symbol.name: capture.depth for capture in c.captures}
    assert depths == {"x": 1, "y": 0}
    assert {capture.owner_frame for capture in c.captures} == {"fn_a", "fn_a.b"}
    # b forwards the chain: it receives a's environment and builds one for c.
    assert frames["fn_a.b"].needs_env and frames["fn_a.b"].environment is not None
    assert not frames["fn_a"].needs_env
    # the lexical distance is never the dynamic caller: control link != access link
    assert c.slot("control_link").offset != c.slot("access_link").offset


def test_captured_parameter_keeps_its_parameter_slot(compile_facts):
    source = """
    function outer(p: integer): integer {
      function inner(): integer { return p; }
      return inner();
    }
    """
    _, facts = compile_facts(source)
    outer = facts.layouts.frame_by_label("fn_outer")
    layout = facts.layouts.symbols.layout_for(outer.slot("p").symbol)
    assert layout.storage.value == "parameter"
    assert layout.captured and layout.env_offset == 0
    assert outer.slot("p").kind is FrameSlotKind.PARAMETER


def test_recursion_and_global_references_are_not_captures(compile_facts):
    source = """
    let total: integer = 0;
    function fact(n: integer): integer {
      if (n <= 1) { return total + 1; }
      return n * fact(n - 1);
    }
    function par(n: integer): boolean { return n == 0 || impar(n - 1); }
    function impar(n: integer): boolean { return n != 0 && par(n - 1); }
    """
    _, facts = compile_facts(source)
    for frame in facts.layouts.frames:
        assert not frame.captures and not frame.needs_env and frame.environment is None


def test_a_function_that_only_returns_never_declares_a_capture_it_does_not_use(compile_facts):
    source = """
    function f(): integer {
      let usada: integer = 1;
      let ignorada: integer = 2;
      function g(): integer { return usada; }
      return g() + ignorada;
    }
    """
    _, facts = compile_facts(source)
    f = facts.layouts.frame_by_label("fn_f")
    assert [slot.symbol.name for slot in f.environment.slots] == ["usada"]
    assert f.slot("ignorada").kind is FrameSlotKind.LOCAL


def test_environment_is_heap_only_when_the_closure_can_escape(compile_facts):
    direct = """
    function f(): integer {
      let x: integer = 1;
      function g(): integer { return x; }
      return g();
    }
    """
    escaping = """
    function f(): integer {
      let x: integer = 1;
      function g(): integer { return x; }
      let guardada = g;
      return 0;
    }
    """
    _, stack = compile_facts(direct)
    _, heap = compile_facts(escaping)
    assert stack.layouts.frame_by_label("fn_f").environment.heap is False
    assert heap.layouts.frame_by_label("fn_f").environment.heap is True


def test_without_the_syntax_tree_every_environment_is_conservatively_heap(compile_facts):
    source = """
    function f(): integer {
      let x: integer = 1;
      function g(): integer { return x; }
      return g();
    }
    """
    _, facts = compile_facts(source, with_tree=False)
    assert facts.layouts.frame_by_label("fn_f").environment.heap is True


def test_frame_lookup_by_symbol_and_label(compile_facts):
    source = "function f(): integer { return 1; }\nlet r = f();\n"
    run, facts = compile_facts(source)
    function = run.semantic_result.symbol_table.global_scope.resolve_local("f")
    assert facts.layouts.frame_for(function).label == "fn_f"
    assert facts.layouts.frame_by_label("global") is facts.layouts.global_frame
    with pytest.raises(LookupError):
        facts.layouts.frame_by_label("fn_none")
    with pytest.raises(LookupError):
        facts.layouts.frame_for(sym("f", kind=SymbolKind.FUNCTION))

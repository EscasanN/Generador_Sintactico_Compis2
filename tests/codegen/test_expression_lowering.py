import pytest

from src.antlr_mode.parse_tree import ParseTreeNode
from src.codegen.builder import IRBuilder
from src.codegen.contracts import Address, CodegenError, ValueRef
from src.codegen.expression_lowering import ExpressionLowerer
from src.codegen.ir import OpCode, Operand, OperandKind
from src.codegen.verifier import IRVerifier
from src.semantic.diagnostics import SourceLocation
from src.semantic.symbol_table import Symbol, SymbolKind
from src.semantic.types import BOOLEAN, INTEGER, NULL
from src.semantic.values import SemanticValue


LOC = SourceLocation(1, 1)


class FakeSemanticFacts:
    def __init__(self):
        self.values = {}
        self.symbols = {}
        self.addresses = {}

    def value_for(self, node):
        return self.values[id(node)]

    def symbol_for(self, node):
        return self.symbols.get(id(node))

    def scope_for(self, node):
        return None

    def address_for(self, symbol):
        return self.addresses[id(symbol)]

    def member_offset(self, owner, name):
        raise NotImplementedError

    def lexical_access(self, node, symbol):
        raise NotImplementedError


def node(alternative, *children, text=None):
    return ParseTreeNode(
        "expr", list(children), rule_name="expression",
        alternative=alternative, text=text, line=1, column=1,
    )


def literal(facts, value, type_):
    item = node("NullLiteral" if value is None else "Literal", text=str(value))
    facts.values[id(item)] = SemanticValue(type_, value, location=LOC)
    return item


def identifier(facts, symbol):
    item = node("IdentifierExpr", text=symbol.name)
    facts.values[id(item)] = SemanticValue(symbol.type, symbol=symbol, location=LOC)
    facts.symbols[id(item)] = symbol
    facts.addresses[id(symbol)] = Address(symbol, "global", symbol.name)
    return item


def setup():
    builder = IRBuilder()
    facts = FakeSemanticFacts()
    return builder, facts, ExpressionLowerer(builder, facts)


def test_literals_and_null_are_typed_immediates_without_instructions():
    builder, facts, lowerer = setup()
    number = lowerer.lower(literal(facts, 5, INTEGER))
    null = lowerer.lower(literal(facts, None, NULL))
    assert number.operand.value == 5
    assert null.operand.value is None
    assert number.owns_temporary is False
    assert builder.build().global_code == ()


def test_tree_structure_controls_precedence_and_left_to_right_evaluation():
    builder, facts, lowerer = setup()
    x = literal(facts, 2, INTEGER)
    y = literal(facts, 3, INTEGER)
    z = literal(facts, 4, INTEGER)
    product = node("MulExpr", y, z)
    root = node("AddExpr", x, product)
    facts.values[id(product)] = SemanticValue(INTEGER, location=LOC)
    facts.values[id(root)] = SemanticValue(INTEGER, location=LOC)
    result = lowerer.lower(root)
    instructions = builder.build().global_code
    assert [item.opcode for item in instructions] == [OpCode.MUL, OpCode.ADD, OpCode.RELEASE]
    assert instructions[0].arg1.value == 3
    assert instructions[1].arg1.value == 2
    assert result.owns_temporary
    assert IRVerifier().verify(builder.build()) == ()


def test_real_expression_wrapper_without_alternative_is_transparent():
    builder, facts, lowerer = setup()
    inner = literal(facts, 8, INTEGER)
    wrapper = ParseTreeNode(
        "expression", [inner], rule_name="expression", line=1, column=1
    )
    assert lowerer.lower(wrapper).operand.value == 8
    assert builder.build().global_code == ()


def test_left_symbol_value_is_frozen_before_rhs_assignment():
    builder, facts, lowerer = setup()
    declaration = Symbol("x", SymbolKind.VARIABLE, INTEGER, True, LOC)
    left = identifier(facts, declaration)
    lhs = identifier(facts, declaration)
    assignment = node("AssignExpr", lhs, literal(facts, 2, INTEGER))
    facts.values[id(assignment)] = SemanticValue(INTEGER, location=LOC)
    root = node("AddExpr", left, assignment)
    facts.values[id(root)] = SemanticValue(INTEGER, location=LOC)
    lowerer.lower(root)
    code = builder.build().global_code
    reads = [i for i, item in enumerate(code) if item.opcode is OpCode.COPY]
    assert code[reads[0]].arg1.kind is OperandKind.SYMBOL
    assert code[reads[0]].result.kind is OperandKind.TEMPORARY
    assert code[reads[1]].result.kind is OperandKind.SYMBOL
    assert code[reads[0]].result == next(item for item in code if item.opcode is OpCode.ADD).arg1
    assert IRVerifier().verify(builder.build()) == ()


def test_symbol_snapshot_preserves_source_path():
    builder, facts, lowerer = setup()
    location = SourceLocation(7, 4, source_path="sample.cps")
    declaration = Symbol("x", SymbolKind.VARIABLE, INTEGER, True, location)
    left = identifier(facts, declaration)
    root = node("AddExpr", left, literal(facts, 2, INTEGER))
    facts.values[id(root)] = SemanticValue(INTEGER, location=location)
    lowerer.lower(root)
    assert all(item.source_location == location for item in builder.build().global_code)


@pytest.mark.parametrize("alternative,opcode", [
    ("SubExpr", OpCode.SUB), ("DivExpr", OpCode.DIV), ("ModExpr", OpCode.MOD),
    ("EqualsExpr", OpCode.EQ), ("NotEqualsExpr", OpCode.NE),
    ("LessExpr", OpCode.LT), ("LessEqualExpr", OpCode.LE),
    ("GreaterExpr", OpCode.GT), ("GreaterEqualExpr", OpCode.GE),
])
def test_binary_operators_use_closed_opcode_catalog(alternative, opcode):
    builder, facts, lowerer = setup()
    root = node(alternative, literal(facts, 5, INTEGER), literal(facts, 2, INTEGER))
    comparisons = {OpCode.EQ, OpCode.NE, OpCode.LT, OpCode.LE, OpCode.GT, OpCode.GE}
    facts.values[id(root)] = SemanticValue(
        BOOLEAN if opcode in comparisons else INTEGER, location=LOC
    )
    lowerer.lower(root)
    assert builder.build().global_code[0].opcode is opcode


@pytest.mark.parametrize("alternative,opcode", [("NegExpr", OpCode.NEG), ("NotExpr", OpCode.NOT)])
def test_unary_operations_use_semantic_type(alternative, opcode):
    builder, facts, lowerer = setup()
    root = node(alternative, literal(facts, 1, INTEGER))
    facts.values[id(root)] = SemanticValue(
        BOOLEAN if opcode is OpCode.NOT else INTEGER, location=LOC
    )
    lowerer.lower(root)
    assert builder.build().global_code[0].opcode is opcode


@pytest.mark.parametrize("alternative,branch", [
    ("AndExpr", OpCode.IF_FALSE), ("OrExpr", OpCode.IF_TRUE),
])
def test_logical_rhs_is_behind_a_branch(alternative, branch):
    builder, facts, lowerer = setup()
    rhs = node("NotExpr", literal(facts, True, BOOLEAN))
    facts.values[id(rhs)] = SemanticValue(BOOLEAN, location=LOC)
    root = node(alternative, literal(facts, False, BOOLEAN), rhs)
    facts.values[id(root)] = SemanticValue(BOOLEAN, location=LOC)
    value = lowerer.lower(root)
    opcodes = [item.opcode for item in builder.build().global_code]
    assert opcodes.index(branch) < opcodes.index(OpCode.NOT)
    assert value.owns_temporary
    assert IRVerifier().verify(builder.build()) == ()


def test_ternary_branches_merge_into_one_live_result():
    builder, facts, lowerer = setup()
    true_arm = node("NegExpr", literal(facts, 3, INTEGER))
    false_arm = node("NegExpr", literal(facts, 4, INTEGER))
    root = node("TernaryExpr", literal(facts, True, BOOLEAN), true_arm, false_arm)
    for item in (true_arm, false_arm, root):
        facts.values[id(item)] = SemanticValue(INTEGER, location=LOC)
    value = lowerer.lower(root)
    code = builder.build().global_code
    assert [item.opcode for item in code].count(OpCode.NEG) == 2
    opcodes = [item.opcode for item in code]
    assert opcodes.index(OpCode.GOTO) < opcodes.index(OpCode.NEG, 3)
    assert value.owns_temporary
    assert builder.temporaries.is_active(value.operand)
    assert IRVerifier().verify(builder.build()) == ()


def test_assignment_uses_resolved_symbol_identity():
    builder, facts, lowerer = setup()
    declaration = Symbol("x", SymbolKind.VARIABLE, INTEGER, True, LOC)
    lhs = identifier(facts, declaration)
    rhs = literal(facts, 9, INTEGER)
    root = node("AssignExpr", lhs, rhs)
    facts.values[id(root)] = SemanticValue(INTEGER, location=LOC)
    lowerer.lower(root)
    store = next(item for item in builder.build().global_code if item.opcode is OpCode.COPY)
    assert store.result.kind is OperandKind.SYMBOL
    assert store.result.value.symbol is declaration


def test_assignment_to_member_is_not_misread_as_base_symbol():
    _, facts, lowerer = setup()
    declaration = Symbol("obj", SymbolKind.VARIABLE, INTEGER, True, LOC)
    member = node("PropertyAccessExpr", identifier(facts, declaration))
    root = node("AssignExpr", member, literal(facts, 9, INTEGER))
    facts.values[id(root)] = SemanticValue(INTEGER, location=LOC)
    with pytest.raises(CodegenError, match="IRGEN-UNSUPPORTED-NODE"):
        lowerer.lower(root)


def test_public_primitive_for_list_load_keeps_result_alive_and_consumes_inputs():
    builder, facts, lowerer = setup()
    array = lowerer.lower(literal(facts, None, NULL))
    index = lowerer.lower(literal(facts, 0, INTEGER))
    result = lowerer.emit_value(OpCode.LIST_GET, array, index, INTEGER, LOC)
    assert result.owns_temporary
    assert builder.build().global_code[0].opcode is OpCode.LIST_GET
    assert IRVerifier().verify(builder.build()) == ()


def test_public_call_primitive_counts_parameters():
    builder, facts, lowerer = setup()
    arg = lowerer.lower(literal(facts, 3, INTEGER))
    result = lowerer.emit_call(
        Operand(OperandKind.LABEL, "fn"), [arg], INTEGER, LOC
    )
    assert result is not None and result.owns_temporary
    assert [item.opcode for item in builder.build().global_code] == [OpCode.PARAM, OpCode.CALL]
    assert IRVerifier().verify(builder.build()) == ()


def test_lowering_preserves_semantic_source_path_on_instructions():
    builder, facts, lowerer = setup()
    root = node("AddExpr", literal(facts, 1, INTEGER), literal(facts, 2, INTEGER))
    location = SourceLocation(7, 4, source_path="sample.cps")
    facts.values[id(root)] = SemanticValue(INTEGER, location=location)
    lowerer.lower(root)
    assert all(item.source_location == location for item in builder.build().global_code)


def test_public_value_primitive_consumes_aliased_input_only_once():
    builder, _, lowerer = setup()
    temporary = builder.temporary(INTEGER)
    builder.emit(
        OpCode.COPY, Operand(OperandKind.CONSTANT, 2, INTEGER),
        result=temporary, location=LOC,
    )
    shared = ValueRef(temporary, INTEGER, True, LOC)
    result = lowerer.emit_value(OpCode.ADD, shared, shared, INTEGER, LOC)
    assert builder.temporaries.is_active(result.operand)
    assert IRVerifier().verify(builder.build()) == ()


def test_public_store_primitive_retains_value_when_it_is_also_base():
    builder, _, lowerer = setup()
    temporary = builder.temporary(INTEGER)
    builder.emit(
        OpCode.COPY, Operand(OperandKind.CONSTANT, 2, INTEGER),
        result=temporary, location=LOC,
    )
    shared = ValueRef(temporary, INTEGER, True, LOC)
    index = ValueRef(Operand(OperandKind.CONSTANT, 0, INTEGER), INTEGER)
    retained = lowerer.emit_store(OpCode.LIST_SET, shared, index, shared, LOC)
    assert builder.temporaries.is_active(retained.operand)
    assert IRVerifier().verify(builder.build()) == ()


def test_closure_call_can_use_a_symbol_target():
    builder, _, lowerer = setup()
    target = Operand(OperandKind.SYMBOL, "global@closure", INTEGER)
    lowerer.emit_call(target, [], INTEGER, LOC, closure=True)
    assert IRVerifier().verify(builder.build()) == ()


def test_public_call_keeps_repeated_argument_live_until_call():
    builder, _, lowerer = setup()
    temporary = builder.temporary(INTEGER)
    builder.emit(
        OpCode.COPY, Operand(OperandKind.CONSTANT, 2, INTEGER),
        result=temporary, location=LOC,
    )
    argument = ValueRef(temporary, INTEGER, True, LOC)
    lowerer.emit_call(Operand(OperandKind.LABEL, "fn"), [argument, argument], INTEGER, LOC)
    assert [item.opcode for item in builder.build().global_code] == [
        OpCode.COPY, OpCode.PARAM, OpCode.PARAM, OpCode.CALL, OpCode.RELEASE,
    ]
    assert IRVerifier().verify(builder.build()) == ()


def test_public_argument_lowering_captures_values_before_later_side_effects():
    builder, facts, lowerer = setup()
    declaration = Symbol("x", SymbolKind.VARIABLE, INTEGER, True, LOC)
    first = identifier(facts, declaration)
    assignment = node(
        "AssignExpr", identifier(facts, declaration), literal(facts, 2, INTEGER)
    )
    facts.values[id(assignment)] = SemanticValue(INTEGER, location=LOC)
    arguments = lowerer.lower_arguments([first, assignment])
    lowerer.emit_call(Operand(OperandKind.LABEL, "fn"), arguments, INTEGER, LOC)
    code = builder.build().global_code
    first_param = next(item for item in code if item.opcode is OpCode.PARAM)
    assert first_param.arg1.kind is OperandKind.TEMPORARY
    assert code[0].opcode is OpCode.COPY
    assert code[0].arg1.kind is OperandKind.SYMBOL
    assert IRVerifier().verify(builder.build()) == ()


def test_missing_semantic_fact_is_explicit_internal_error():
    _, _, lowerer = setup()
    with pytest.raises(CodegenError, match="IRGEN-MISSING-FACT"):
        lowerer.lower(node("NegExpr", node("Literal")))


def test_missing_semantic_value_returned_as_none_is_internal_error():
    _, facts, lowerer = setup()
    item = node("Literal")
    facts.values[id(item)] = None
    with pytest.raises(CodegenError, match="IRGEN-MISSING-FACT"):
        lowerer.lower(item)


def test_missing_symbol_address_is_internal_error():
    _, facts, lowerer = setup()
    declaration = Symbol("x", SymbolKind.VARIABLE, INTEGER, True, LOC)
    item = identifier(facts, declaration)
    facts.addresses.clear()
    with pytest.raises(CodegenError, match="IRGEN-MISSING-ADDRESS"):
        lowerer.lower(item)

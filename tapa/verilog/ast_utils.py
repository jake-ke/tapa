"""Verilog abstract syntax tree (AST) nodes and utilities.

This module is designed as a drop-in replacement for `pyverilog.vparser.ast`
with convenient utilities.
"""

from __future__ import annotations

__copyright__ = """
Copyright (c) 2024 RapidStream Design Automation, Inc. and contributors.
All rights reserved. The contributor(s) of this file has/have agreed to the
RapidStream Contributor License Agreement.
"""


from typing import TYPE_CHECKING

from pyverilog.vparser.ast import (
    Block,
    Case,
    CaseStatement,
    Identifier,
    IfStatement,
    IntConst,
    Node,
    Operator,
    PortArg,
    Pragma,
    PragmaEntry,
    StringConst,
    Width,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

# Please keep `make_*` functions sorted by their name.


def make_block(statements: Iterable[Node] | Node, **kwargs: object) -> Block:
    if isinstance(statements, Node):
        statements = (statements,)
    return Block(statements=tuple(statements), **kwargs)


def make_case_with_block(
    comp: Node,
    cases: Iterable[tuple[Iterable[Node] | Node, Iterable[Node] | Node]],
) -> CaseStatement:
    return CaseStatement(
        comp=comp,
        caselist=(
            Case(
                cond=(cond,) if isinstance(cond, Node) else cond,
                statement=make_block(statement),
            )
            for cond, statement in cases
        ),
    )


def make_if_with_block(
    cond: Node,
    true: Iterable[Node] | Node,
    false: Iterable[Node] | Node | None = None,
) -> IfStatement:
    if not (false is None or isinstance(false, IfStatement)):
        false = make_block(false)
    return IfStatement(
        cond=cond,
        true_statement=make_block(true),
        false_statement=false,
    )


def make_int(value: int, width: int = 0) -> IntConst:
    return IntConst(f"{width or value.bit_length() or 1}'d{value}")


def make_operation(operator: type[Operator], nodes: Iterable[Node]) -> Operator | Node:
    """Make a multi-operand operation node out of an iterable of Nodes.

    Note that the nodes appears in the reverse order of the iterable (to avoid
    unnecessary parentheses).

    Args:
    ----
      op: Operator.
      nodes: Iterable of Node. If empty, raises StopIteration.

    Returns:
    -------
      Operator of the result.

    """
    iterator = iter(nodes)
    node = next(iterator)
    try:
        return operator(make_operation(operator, iterator), node)
    except StopIteration:
        return node


def make_pragma(name: str, value: str | None = None) -> Pragma:
    if value is None:
        return Pragma(PragmaEntry(name))
    return Pragma(PragmaEntry(name, StringConst(value)))


def make_port_arg(port: str, arg: str | Node) -> PortArg:
    """Make PortArg from port and arg names.

    Args:
    ----
        port: Port name.
        arg: Arg name (will be used to construct an Identifier) or Node.

    Returns:
    -------
        PortArg: `.port(arg)` in Verilog.

    """
    return PortArg(
        portname=port,
        argname=arg if isinstance(arg, Node) else Identifier(arg),
    )


def make_width(width: int) -> Width | None:
    if width > 0:
        return Width(msb=IntConst(width - 1), lsb=IntConst(0))
    return None
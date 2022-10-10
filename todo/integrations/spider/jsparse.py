import functools
from typing import Any

import pyparsing as pp
import pyparsing.common as ppc


class JSParser:
    pp.ParserElement.enablePackrat()
    expr = pp.Forward()

    identifier = pp.Regex(r"[a-zA-Z_][a-zA-Z0-9_]*")
    number = ppc.number  # type: ignore
    string = pp.quoted_string.set_parse_action(pp.removeQuotes)
    bool = pp.one_of("true false").set_parse_action(lambda s, l, t: t[0] == "true")
    array = pp.Group(
        pp.Literal("[").suppress()
        + (expr + pp.Literal(",")[0, 1].suppress())[...]
        + pp.Literal("]").suppress()
    ).set_parse_action(lambda s, l, t: t.as_list())
    hashable = string | number | bool | identifier
    map = (
        pp.Literal("{").suppress()
        + pp.Dict(
            pp.Group(
                hashable
                + pp.Literal(":").suppress()
                + expr
                + pp.Literal(",")[0, 1].suppress()
            )[...]
        )
        + pp.Literal("}").suppress()
    ).set_parse_action(lambda s, l, t: t.as_dict())
    null = pp.Literal("null").set_parse_action(lambda s, l, t: None)
    # A.B dot access
    access = pp.Combine(identifier + ("." + identifier)[1, ...])
    # enclosure
    enclosure = pp.Group(
        pp.Literal("(").suppress() + expr + pp.Literal(")").suppress()
    ).set_parse_action(lambda s, l, t: t[0])
    # call
    callee = access | identifier | enclosure
    call = callee("callee") + pp.Group(
        pp.Literal("(").suppress()
        + (expr + pp.Literal(",")[0, 1].suppress())[...]
        + pp.Literal(")").suppress()
    ).set_parse_action(lambda s, l, t: t.as_list())("args")
    # atom
    atom = (
        call
        | access
        | map
        | array
        | string
        | bool
        | null
        | identifier
        | number
        | enclosure
    )
    # common binary operators
    bin_expr = pp.Group(
        atom + (pp.one_of("&& || == === != !== > >= < <= + - * / %") + atom)[1, ...],
        aslist=True,
    )
    expr << (bin_expr | atom)

    assignable = access | identifier
    assign = pp.Group(assignable + (pp.Suppress("=") + expr)[1, ...])

    var_decl = pp.Group(
        pp.Optional(pp.one_of(["var", "let"]))
        + pp.OneOrMore(assign + pp.Literal(",")[0, 1].suppress())("assigns")
        + (pp.Literal(";") | pp.LineEnd())
    )
    expr_stmt = pp.Group(expr + (pp.Literal(";") | pp.LineEnd()))
    stmt = expr_stmt | var_decl
    prog = pp.ZeroOrMore(stmt)

    def __init__(self, js: str):
        """
        Parse a JavaScript program and evaluate it.

        :param js: the JavaScript program
        """
        self.js = js

    @functools.cached_property
    def variables(self) -> dict[Any, Any]:
        """
        Parse the javascript code and return a dict of variables.
        Limitations:
        - Expression are not evaluated, but returned as [operand, operator,
          operand]. Precedence is not considered.
        - Only support var and let declaration & function call.

        :return: the variables
        """

        variables = {}
        for result in self.prog.parse_string(self.js):
            if not hasattr(result, "assigns"):
                continue
            for assign in result.assigns:
                for i in range(len(assign) - 1):
                    variables[assign[i]] = assign[-1]
        return variables

    def __getitem__(self, name: str) -> Any:
        return self.variables[name]

    def __getattr__(self, item) -> Any:
        try:
            return self[item]
        except KeyError:
            raise AttributeError(f'"{item}" is not a variable')

    def get(self, name: str, default: Any = None) -> Any:
        return self.variables.get(name, default)

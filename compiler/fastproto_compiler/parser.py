from rply import ParserGenerator

from .lexer import lex
from .model import (
    ArrayType,
    ExplicitIdentifier,
    FastprotoError,
    Field,
    Identifier,
    Message,
    NamespaceNode,
    Program,
    State,
    Type,
)


def parser():
    pg = ParserGenerator(
        [
            "NUMBER",
            "NAMESPACE",
            "MESSAGE",
            "COLONCOLON",
            "COLON",
            "LPAREN",
            "RPAREN",
            "LBRACE",
            "RBRACE",
            "SEMICOLON",
            "IDENTIFIER",
            "LANGLE",
            "RANGLE",
            "ARRAY",
        ]
    )

    @pg.production("program : namespace")
    @pg.production("program : program namespace")
    def program(p):
        if len(p) == 1:
            return Program().add_namespace(p[0])
        return p[0].add_namespace(p[1])

    @pg.production("namespace_element : namespace")
    @pg.production("namespace_element : message")
    def namespace_element(p):
        return p[0]

    @pg.production("namespace_body : namespace_body namespace_element")
    @pg.production("namespace_body : namespace_element")
    def namespace_body(p):
        if len(p) == 1:
            return [p[0]]
        return p[0] + [p[1]]

    @pg.production("identifier : IDENTIFIER")
    @pg.production("identifier : identifier COLONCOLON IDENTIFIER")
    def identifier(p):
        if len(p) == 1:
            return Identifier(p[0].getstr())
        return p[0].make_explicit(p[2].getstr())

    @pg.production("namespace_name : IDENTIFIER")
    @pg.production("namespace_name : namespace_name COLONCOLON IDENTIFIER")
    def namespace_name(p):
        if len(p) == 1:
            return (p[0].getstr(),)
        return p[0] + (p[2].getstr(),)

    @pg.production("namespace : NAMESPACE namespace_name LBRACE namespace_body RBRACE")
    @pg.production("namespace : NAMESPACE namespace_name LBRACE RBRACE")
    def namespace(p):
        if len(p) == 4:
            return NamespaceNode(p[1], [])
        return NamespaceNode(p[1], p[3])

    @pg.production("type : identifier")
    @pg.production("type : ARRAY LANGLE identifier RANGLE")
    def type_(p):
        if len(p) == 1:
            return Type(p[0])
        return ArrayType(p[2])

    @pg.production("field : IDENTIFIER COLON type SEMICOLON")
    def field(p):
        return Field(p[0].getstr(), p[2])

    @pg.production("field_list : field_list field")
    @pg.production("field_list : field")
    def field_list(p):
        if len(p) == 1:
            return [p[0]]
        return p[0] + [p[1]]

    @pg.production(
        "message : MESSAGE IDENTIFIER LPAREN NUMBER RPAREN LBRACE field_list RBRACE"
    )
    @pg.production("message : MESSAGE IDENTIFIER LPAREN NUMBER RPAREN LBRACE RBRACE")
    def message(p):
        if len(p) == 7:
            return Message(p[1].getstr(), int(p[3].getstr()))
        return Message(p[1].getstr(), int(p[3].getstr()), p[6])

    @pg.error
    def error_handler(token):
        if token is None:
            raise FastprotoError("Unexpected end of input")

        position = token.getsourcepos()
        raise FastprotoError(
            f"Unexpected token {token.gettokentype()} at line {position.lineno}, "
            f"column {position.colno}: {token.getstr()!r}"
        )

    return pg.build()


def parse(tokens):
    return parser().parse(tokens)


def parse_source(source: str):
    return parse(lex(source))


def compile_source(source: str):
    return parse_source(source).eval(State())

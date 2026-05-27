from rply import LexerGenerator


def lexer():
    lg = LexerGenerator()
    lg.add("NUMBER", r"\d+")
    lg.add("NAMESPACE", r"\bnamespace\b")
    lg.add("MESSAGE", r"\bmessage\b")
    lg.add("ARRAY", r"\barray\b")
    lg.add("COLONCOLON", r"::")
    lg.add("COLON", r":")
    lg.add("LPAREN", r"\(")
    lg.add("RPAREN", r"\)")
    lg.add("LBRACE", r"\{")
    lg.add("RBRACE", r"\}")
    lg.add("SEMICOLON", r";")
    lg.add("IDENTIFIER", r"[a-zA-Z_][a-zA-Z0-9_]*")
    lg.add("LANGLE", r"<")
    lg.add("RANGLE", r">")
    lg.ignore(r"//[^\n]*")
    lg.ignore(r"/\*[\s\S]*?\*/")
    lg.ignore(r"\s+")
    return lg.build()


def lex(source: str):
    return lexer().lex(source)

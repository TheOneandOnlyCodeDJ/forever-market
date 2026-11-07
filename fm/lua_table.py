"""Parser for WoW SavedVariables files: `VAR = { ... }` -> {"VAR": python value}. No eval."""
import re

TOKEN = re.compile(r"""\s+|--[^\n]*|"(?:[^"\\]|\\.)*"|-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?|[A-Za-z_]\w*|[{}\[\]=,;]""", re.S)
ESCAPE = re.compile(r"\\(\d{1,3}|.)", re.S)
SIMPLE = {"n": "\n", "t": "\t", "r": "\r", "a": "\a", "b": "\b", "f": "\f", "v": "\v", "\n": "\n"}
WORDS = {"true": True, "false": False, "nil": None}


def _tokens(text):
    pos, out = 0, []
    while pos < len(text):
        m = TOKEN.match(text, pos)
        if not m:
            raise ValueError(f"unexpected character {text[pos]!r} at offset {pos}")
        if not m.group().isspace() and not m.group().startswith("--"):
            out.append(m.group())
        pos = m.end()
    return out


def _unescape(m):
    e = m.group(1)
    return chr(int(e)) if e.isdigit() else SIMPLE.get(e, e)


class _Parser:
    def __init__(self, text):
        self.toks, self.i = _tokens(text), 0

    def next(self, expect=None):
        tok = self.toks[self.i] if self.i < len(self.toks) else None
        if expect is not None and tok != expect:
            raise ValueError(f"expected {expect!r}, got {tok!r} at token {self.i}")
        self.i += 1
        return tok

    def peek(self, k=0):
        return self.toks[self.i + k] if self.i + k < len(self.toks) else None

    def value(self):
        tok = self.next()
        if tok == "{":
            return self.table()
        if tok is None:
            raise ValueError("unexpected end of input")
        if tok[0] == '"':
            return ESCAPE.sub(_unescape, tok[1:-1])
        if tok in WORDS:
            return WORDS[tok]
        if re.fullmatch(r"-?\d+", tok):
            return int(tok)
        try:
            return float(tok)
        except ValueError:
            raise ValueError(f"unexpected token {tok!r} at token {self.i - 1}") from None

    def table(self):
        """Keyed or mixed tables -> dict; purely positional -> list; `{}` -> {}."""
        keyed, seq = {}, []
        while self.peek() != "}":
            if self.peek() == "[":
                self.next()
                key = self.value()
                self.next("]")
                self.next("=")
                keyed[key] = self.value()
            elif self.peek(1) == "=" and re.fullmatch(r"[A-Za-z_]\w*", self.peek() or ""):
                key = self.next()
                self.next("=")
                keyed[key] = self.value()
            else:
                seq.append(self.value())
            if self.peek() in (",", ";"):
                self.next()
            elif self.peek() != "}":
                raise ValueError(f"expected ',' or '}}', got {self.peek()!r} at token {self.i}")
        self.next("}")
        if not keyed:
            return seq or {}
        keyed.update({n: v for n, v in enumerate(seq, 1)})
        return keyed


def parse(text):
    p, out = _Parser(text), {}
    while p.peek() is not None:
        name = p.next()
        p.next("=")
        out[name] = p.value()
    return out

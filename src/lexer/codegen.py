"""
codegen.py — Módulo 8: Generador de Código

Responsabilidades:
  - Serializa la tabla de transiciones del DFA minimizado como JSON de Java.
  - Genera el motor nextToken() con política de maximal munch.
  - Integra las acciones semánticas de la especificación original.
  - Produce un archivo .java listo para compilar como analizador léxico.

Entrada:  DFA minimizado  +  ResolvedSpec
Salida:   archivo .java del analizador léxico generado
"""

from __future__ import annotations

import json
import os
import re
import textwrap
from datetime import datetime

from src.lexer.dfa import DFA
from src.lexer.resolver import ResolvedSpec


# ══════════════════════════════════════════════════════════════════════════════
#  Excepción
# ══════════════════════════════════════════════════════════════════════════════


class CodeGenError(Exception):
    """Error durante la generación de código."""


# ══════════════════════════════════════════════════════════════════════════════
#  Generador
# ══════════════════════════════════════════════════════════════════════════════


class LexerCodeGenerator:
    """
    Genera el código fuente Java del analizador léxico a partir del DFA minimizado.

    Uso:
        gen = LexerCodeGenerator(min_dfa, resolved_spec)
        code = gen.generate()
        gen.write("output/Lexer.java")
    """

    def __init__(self, dfa: DFA, spec: ResolvedSpec) -> None:
        self._dfa = dfa
        self._spec = spec
        self._data_filename = "LexerData.json"

    # ── API pública ───────────────────────────────────────────────────────────

    def generate(self) -> str:
        """Devuelve el código fuente Java del lexer como string."""
        parts: list[str] = [
            self._section_banner(),
            self._section_imports(),
            "public final class Lexer {",
            "",
            self._indent(self._section_token_enum()),
            "",
            self._indent(self._section_token_class()),
            "",
            self._indent(self._section_automaton_data()),
            "",
            self._indent(self._section_lexer_fields()),
            "",
            self._indent(self._section_constructor()),
            "",
            self._indent(self._section_tokenize()),
            "",
            self._indent(self._section_next_token()),
            "",
            self._indent(self._section_helpers()),
            "",
            self._indent(self._section_main()),
            "}",
        ]
        return "\n".join(parts)

    def write(self, output_path: str) -> str:
        """Genera el código y lo escribe en output_path. Devuelve la ruta."""
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        data_path = self._data_output_path(output_path)
        self._data_filename = os.path.basename(data_path)
        code = self.generate()
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(code)
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(self._build_data_payload(), f, ensure_ascii=False, separators=(",", ":"))
        return output_path

    # ── Helpers internos ─────────────────────────────────────────────────────

    @staticmethod
    def _indent(text: str, level: int = 1) -> str:
        prefix = "    " * level
        return textwrap.indent(text, prefix)

    # ── Secciones del archivo generado ───────────────────────────────────────

    def _section_banner(self) -> str:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        spec_name = getattr(self._spec, "source_file", "<spec>")
        return textwrap.dedent(f"""\
            // =============================================================
            //  LEXER GENERADO AUTOMÁTICAMENTE
            //  Generado por: Generador de Analizadores Léxicos
            //  Fecha       : {ts}
            //  Especificación: {spec_name}
            //
            //  NO EDITAR MANUALMENTE — regenerar desde la especificación .yal
            // =============================================================
        """)

    def _section_imports(self) -> str:
        header = _normalize_embedded_code(self._spec.header)
        lines: list[str] = [
            "import java.io.IOException;",
            "import java.nio.file.Files;",
            "import java.nio.file.Paths;",
            "import java.util.ArrayList;",
            "import java.util.HashMap;",
            "import java.util.HashSet;",
            "import java.util.List;",
            "import java.util.Map;",
            "import java.util.Set;",
        ]
        if header:
            lines.append("")
            lines.append("// --- Header ---")
            for h in header.splitlines():
                stripped = h.strip()
                if stripped:
                    lines.append(stripped)
        lines.append("")
        return "\n".join(lines)

    def _section_token_enum(self) -> str:
        tokens: list[str] = []
        seen: set[str] = set()
        for state in self._dfa.accept_states:
            name = _extract_token_name(state.token or "UNKNOWN")
            if name not in seen:
                seen.add(name)
                tokens.append(name)
        tokens_str = ",\n        ".join(tokens + ["EOF", "ERROR"])
        return textwrap.dedent(f"""\
            /** Tipos de tokens reconocidos por el lexer. */
            public enum TokenType {{
                {tokens_str}
            }}
        """)

    def _section_token_class(self) -> str:
        return textwrap.dedent("""\
            /** Representa un token reconocido por el lexer. */
            public static final class Token {

                public final TokenType type;
                public final String    value;
                public final int       line;
                public final int       column;

                public Token(
                        final TokenType type,
                        final String    value,
                        final int       line,
                        final int       column) {
                    this.type   = type;
                    this.value  = value;
                    this.line   = line;
                    this.column = column;
                }

                @Override
                public String toString() {
                    return String.format("Token(%-15s %-20s line=%d col=%d)",
                            type, "\\\"" + escapeLexeme(value) + "\\\"", line, column);
                }
            }
        """)

    def _build_data_payload(self) -> dict[str, object]:
        transitions: dict[str, dict[str, int]] = {}
        for state in sorted(self._dfa.states, key=lambda s: s.state_id):
            transitions[str(state.state_id)] = {
                str(sym): tgt.state_id for sym, tgt in sorted(state.transitions.items())
            }

        accept: dict[str, str] = {}
        for state in sorted(self._dfa.accept_states, key=lambda s: s.state_id):
            accept[str(state.state_id)] = _extract_token_name(state.token or "UNKNOWN")

        skip: list[str] = []
        for state in self._dfa.accept_states:
            action = (state.token or "").strip()
            if not action:
                skip.append(_extract_token_name(state.token or "UNKNOWN"))

        return {
            "start": self._dfa.start.state_id,
            "transitions": transitions,
            "accept": accept,
            "skip": sorted(set(skip)),
        }

    @staticmethod
    def _data_output_path(output_path: str) -> str:
        directory = os.path.dirname(output_path) or "."
        stem = os.path.splitext(os.path.basename(output_path))[0]
        return os.path.join(directory, f"{stem}Data.json")

    def _section_automaton_data(self) -> str:
        return textwrap.dedent(f"""\
            // --- Metadatos del autómata ---
            private static final String DATA_FILE = {json.dumps(self._data_filename)};
            private static final Map<Integer, Map<Integer, Integer>> TRANS;
            private static final Map<Integer, TokenType> ACCEPT;
            private static final Set<TokenType> SKIP;
            private static final int START;

            static {{
                final LexerData data = loadLexerData();
                TRANS = data.transitions;
                ACCEPT = data.accept;
                SKIP = data.skip;
                START = data.start;
            }}
        """)

    def _section_lexer_fields(self) -> str:
        return textwrap.dedent("""\
            // --- Campos del lexer ---
            private final String       source;
            private       int          pos    = 0;
            private       int          line   = 1;
            private       int          col    = 1;
            private final List<String> errors = new ArrayList<>();
        """)

    def _section_constructor(self) -> str:
        return textwrap.dedent("""\
            public Lexer(final String source) {
                this.source = source;
            }
        """)

    def _section_tokenize(self) -> str:
        return textwrap.dedent("""\
            /** Tokeniza todo el texto y devuelve la lista de tokens. */
            public List<Token> tokenize() {
                final List<Token> tokens = new ArrayList<>();
                while (pos < source.length()) {
                    final Token tok = nextToken();
                    if (tok != null) {
                        tokens.add(tok);
                    }
                }
                if (!errors.isEmpty()) {
                    System.err.println("\\n[ERRORES LÉXICOS]");
                    for (final String err : errors) {
                        System.err.println("  " + err);
                    }
                }
                return tokens;
            }

            /** Devuelve una lista inmutable de errores léxicos encontrados. */
            public List<String> getErrors() {
                return List.copyOf(errors);
            }
        """)

    def _section_next_token(self) -> str:
        return textwrap.dedent("""\
            /**
             * Reconoce el siguiente token usando maximal munch sobre el DFA.
             *
             * Algoritmo:
             *   1. Partir del estado inicial del DFA.
             *   2. Consumir caracteres mientras haya transición válida.
             *   3. Cada vez que se llega a un estado de aceptación,
             *      guardar (estado, posición) como último aceptante.
             *   4. Al quedarse sin transición, usar el último aceptante.
             *   5. Si nunca hubo aceptación → error léxico, avanzar 1 char.
             */
            private Token nextToken() {
                final int startPos  = pos;
                final int startLine = line;
                final int startCol  = col;

                int  state           = START;
                int  lastAcceptState = -1;
                int  lastAcceptPos   = startPos;
                int  lastAcceptLine  = startLine;
                int  lastAcceptCol   = startCol;

                if (ACCEPT.containsKey(state)) {
                    lastAcceptState = state;
                    lastAcceptPos   = pos;
                    lastAcceptLine  = line;
                    lastAcceptCol   = col;
                }

                while (pos < source.length()) {
                    final char ch  = source.charAt(pos);
                    final int  sym = (int) ch;

                    final Map<Integer, Integer> row = TRANS.get(state);
                    if (row == null || !row.containsKey(sym)) {
                        break;
                    }

                    state = row.get(sym);
                    pos++;
                    if (ch == '\\n') {
                        line++;
                        col = 1;
                    } else {
                        col++;
                    }

                    if (ACCEPT.containsKey(state)) {
                        lastAcceptState = state;
                        lastAcceptPos   = pos;
                        lastAcceptLine  = line;
                        lastAcceptCol   = col;
                    }
                }

                if (lastAcceptState == -1) {
                    final char bad = source.charAt(startPos);
                    errors.add(String.format(
                            "Linea %d, col %d: caracter no reconocido '%s'",
                            startLine, startCol, printableChar(bad)));
                    pos = startPos + 1;
                    if (bad == '\\n') {
                        line = startLine + 1;
                        col = 1;
                    } else {
                        line = startLine;
                        col = startCol + 1;
                    }
                    return null;
                }

                pos  = lastAcceptPos;
                line = lastAcceptLine;
                col  = lastAcceptCol;

                final String    lexeme    = source.substring(startPos, lastAcceptPos);
                final TokenType tokenType = ACCEPT.get(lastAcceptState);

                if (SKIP.contains(tokenType)) {
                    return null;
                }

                return new Token(tokenType, lexeme, startLine, startCol);
            }
        """)

    def _section_helpers(self) -> str:
        lines = [textwrap.dedent("""\
            private static String escapeLexeme(final String value) {
                final StringBuilder sb = new StringBuilder(value.length());
                for (int i = 0; i < value.length(); i++) {
                    final char ch = value.charAt(i);
                    switch (ch) {
                        case '\\n' -> sb.append("\\\\n");
                        case '\\r' -> sb.append("\\\\r");
                        case '\\t' -> sb.append("\\\\t");
                        case '\\\\' -> sb.append("\\\\\\\\");
                        case '"' -> sb.append("\\\\\\\"");
                        default -> {
                            if (Character.isISOControl(ch)) {
                                sb.append(String.format("\\\\u%04x", (int) ch));
                            } else {
                                sb.append(ch);
                            }
                        }
                    }
                }
                return sb.toString();
            }

            private static String printableChar(final char ch) {
                return escapeLexeme(String.valueOf(ch));
            }

            private static LexerData loadLexerData() {
                try {
                    java.nio.file.Path basePath = Paths.get(
                            Lexer.class.getProtectionDomain().getCodeSource().getLocation().toURI());
                    if (Files.isRegularFile(basePath)) {
                        basePath = basePath.getParent();
                    }
                    final String json = Files.readString(basePath.resolve(DATA_FILE));
                    final JsonCursor cursor = new JsonCursor(json);
                    return parseLexerData(cursor);
                } catch (Exception ex) {
                    throw new IllegalStateException(
                            "No se pudo cargar el archivo de datos del lexer: " + DATA_FILE,
                            ex);
                }
            }

            private static LexerData parseLexerData(final JsonCursor cursor) {
                Map<Integer, Map<Integer, Integer>> transitions = new HashMap<>();
                Map<Integer, TokenType> accept = new HashMap<>();
                Set<TokenType> skip = new HashSet<>();
                Integer start = null;

                cursor.expect('{');
                if (!cursor.consume('}')) {
                    do {
                        final String key = cursor.parseString();
                        cursor.expect(':');
                        switch (key) {
                            case "start" -> start = cursor.parseInt();
                            case "transitions" -> transitions = parseTransitionTable(cursor);
                            case "accept" -> accept = parseAcceptStates(cursor);
                            case "skip" -> skip = parseSkipTokens(cursor);
                            default -> throw new IllegalArgumentException(
                                    "Clave no soportada en lexer data: " + key);
                        }
                    } while (cursor.consume(','));

                    cursor.expect('}');
                }

                cursor.ensureEnd();
                if (start == null) {
                    throw new IllegalArgumentException(
                            "Falta la clave 'start' en el archivo de datos del lexer");
                }
                return new LexerData(transitions, accept, skip, start);
            }

            private static Map<Integer, Map<Integer, Integer>> parseTransitionTable(
                    final JsonCursor cursor) {
                final Map<Integer, Map<Integer, Integer>> result = new HashMap<>();

                cursor.expect('{');
                if (cursor.consume('}')) {
                    return result;
                }

                do {
                    final int state = Integer.parseInt(cursor.parseString());
                    cursor.expect(':');
                    result.put(state, parseIntMap(cursor));
                } while (cursor.consume(','));

                cursor.expect('}');
                return result;
            }

            private static Map<Integer, TokenType> parseAcceptStates(final JsonCursor cursor) {
                final Map<Integer, TokenType> result = new HashMap<>();

                cursor.expect('{');
                if (cursor.consume('}')) {
                    return result;
                }

                do {
                    final int state = Integer.parseInt(cursor.parseString());
                    cursor.expect(':');
                    result.put(state, TokenType.valueOf(cursor.parseString()));
                } while (cursor.consume(','));

                cursor.expect('}');
                return result;
            }

            private static Set<TokenType> parseSkipTokens(final JsonCursor cursor) {
                final Set<TokenType> result = new HashSet<>();

                cursor.expect('[');
                if (cursor.consume(']')) {
                    return result;
                }

                do {
                    result.add(TokenType.valueOf(cursor.parseString()));
                } while (cursor.consume(','));

                cursor.expect(']');
                return result;
            }

            private static Map<Integer, Integer> parseIntMap(final JsonCursor cursor) {
                final Map<Integer, Integer> result = new HashMap<>();

                cursor.expect('{');
                if (cursor.consume('}')) {
                    return result;
                }

                do {
                    final int key = Integer.parseInt(cursor.parseString());
                    cursor.expect(':');
                    result.put(key, cursor.parseInt());
                } while (cursor.consume(','));

                cursor.expect('}');
                return result;
            }

            private static final class JsonCursor {
                private final String text;
                private int index;

                private JsonCursor(final String text) {
                    this.text = text;
                    this.index = 0;
                }

                private void ensureEnd() {
                    skipWhitespace();
                    if (index != text.length()) {
                        throw error("contenido extra al final del JSON");
                    }
                }

                private boolean consume(final char expected) {
                    skipWhitespace();
                    if (index < text.length() && text.charAt(index) == expected) {
                        index++;
                        return true;
                    }
                    return false;
                }

                private void expect(final char expected) {
                    if (!consume(expected)) {
                        throw error("se esperaba '" + expected + "'");
                    }
                }

                private int parseInt() {
                    skipWhitespace();
                    final int start = index;
                    if (index < text.length() && text.charAt(index) == '-') {
                        index++;
                    }
                    final int digitsStart = index;
                    while (index < text.length() && Character.isDigit(text.charAt(index))) {
                        index++;
                    }
                    if (digitsStart == index) {
                        throw error("se esperaba un entero");
                    }
                    return Integer.parseInt(text.substring(start, index));
                }

                private String parseString() {
                    skipWhitespace();
                    expect('"');
                    final StringBuilder sb = new StringBuilder();

                    while (index < text.length()) {
                        final char ch = text.charAt(index++);
                        if (ch == '"') {
                            return sb.toString();
                        }
                        if (ch != '\\\\') {
                            sb.append(ch);
                            continue;
                        }
                        if (index >= text.length()) {
                            throw error("escape incompleto");
                        }
                        final char esc = text.charAt(index++);
                        switch (esc) {
                            case '"' -> sb.append('"');
                            case '\\\\' -> sb.append('\\\\');
                            case '/' -> sb.append('/');
                            case 'b' -> sb.append('\\b');
                            case 'f' -> sb.append('\\f');
                            case 'n' -> sb.append('\\n');
                            case 'r' -> sb.append('\\r');
                            case 't' -> sb.append('\\t');
                            case 'u' -> {
                                if (index + 4 > text.length()) {
                                    throw error("escape unicode incompleto");
                                }
                                final String hex = text.substring(index, index + 4);
                                sb.append((char) Integer.parseInt(hex, 16));
                                index += 4;
                            }
                            default -> throw error("escape no soportado: " + esc);
                        }
                    }

                    throw error("cadena JSON sin cerrar");
                }

                private void skipWhitespace() {
                    while (index < text.length() && Character.isWhitespace(text.charAt(index))) {
                        index++;
                    }
                }

                private IllegalArgumentException error(final String message) {
                    return new IllegalArgumentException(
                            message + " en indice " + index + ": " + text);
                }
            }

            private static final class LexerData {
                private final Map<Integer, Map<Integer, Integer>> transitions;
                private final Map<Integer, TokenType> accept;
                private final Set<TokenType> skip;
                private final int start;

                private LexerData(
                        final Map<Integer, Map<Integer, Integer>> transitions,
                        final Map<Integer, TokenType> accept,
                        final Set<TokenType> skip,
                        final int start) {
                    this.transitions = transitions;
                    this.accept = accept;
                    this.skip = skip;
                    this.start = start;
                }
            }
        """)]

        trailer = _normalize_embedded_code(self._spec.trailer)
        if trailer:
            lines.append("// --- Trailer ---")
            for t in trailer.splitlines():
                stripped = t.strip()
                if stripped:
                    lines.append(stripped)
        lines.append("")
        return "\n".join(lines)

    def _section_main(self) -> str:
        return textwrap.dedent("""\
            // --- Punto de entrada ---
            public static void main(final String[] args) throws IOException {
                if (args.length < 1) {
                    System.err.println("Uso: java Lexer <archivo.txt>");
                    System.exit(1);
                }

                final String source = Files.readString(Paths.get(args[0]));
                System.out.printf(">>> Analizando: %s%n%n", args[0]);

                final Lexer       lexer  = new Lexer(source);
                final List<Token> tokens = lexer.tokenize();

                System.out.printf("%-20s %-25s %5s  %4s%n",
                        "TOKEN", "LEXEMA", "LINEA", "COL");
                System.out.println("-".repeat(60));
                for (final Token tok : tokens) {
                    System.out.printf("%-20s %-25s %5d  %4d%n",
                            tok.type, "\\\"" + escapeLexeme(tok.value) + "\\\"",
                            tok.line, tok.column);
                }

                System.out.printf("%n>>> Total tokens: %d%n", tokens.size());
                if (!lexer.getErrors().isEmpty()) {
                    System.out.printf(">>> Errores lexicos: %d%n",
                            lexer.getErrors().size());
                    System.exit(1);
                }
            }
        """)


# ══════════════════════════════════════════════════════════════════════════════
#  Utilidades internas
# ══════════════════════════════════════════════════════════════════════════════


def _strip_ocaml_comments(text: str) -> str:
    """Elimina comentarios estilo OCaml (* ... *) de una cadena, soportando anidamiento."""
    result: list[str] = []
    i = 0
    depth = 0
    while i < len(text):
        if i + 1 < len(text) and text[i] == '(' and text[i + 1] == '*':
            depth += 1
            i += 2
            continue
        if i + 1 < len(text) and text[i] == '*' and text[i + 1] == ')':
            if depth > 0:
                depth -= 1
            i += 2
            continue
        if depth == 0:
            result.append(text[i])
        i += 1
    return ''.join(result).strip()


def _normalize_embedded_code(text: str | None) -> str:
    if not text:
        return ""
    clean = _strip_ocaml_comments(text)
    if not clean:
        return ""
    lowered = clean.strip().lower()
    if lowered in {"header", "trailer"}:
        return ""
    return clean.strip()


def _extract_token_name(action: str) -> str:
    """
    Extrae el nombre del token de una cadena de acción.

    Ejemplos:
        "return WHITESPACE"  →  "WHITESPACE"
        "return ID"          →  "ID"
        "(* skip whitespace *)"  →  "__SKIP__"
    """
    action = re.sub(r'\(\*.*?\*\)', '', action).strip()

    if not action:
        return "__SKIP__"

    lower = action.lower()
    if lower.startswith("return"):
        rest = action[6:].strip()
        token = rest.split()[0] if rest.split() else action
        return token.rstrip(";")

    sanitized = re.sub(r'[^A-Za-z0-9_]', '_', action)
    sanitized = re.sub(r'_+', '_', sanitized).strip('_')
    return sanitized if sanitized else "__SKIP__"
# ══════════════════════════════════════════════════════════════════════════════
#  Función de conveniencia
# ══════════════════════════════════════════════════════════════════════════════


def generate_lexer(
    dfa: DFA,
    spec: ResolvedSpec,
    output_path: str = "output/Lexer.java",
) -> str:
    """
    Genera el analizador léxico Java y lo escribe en output_path.

    Parámetros:
        dfa         — DFA minimizado (salida de HopcroftMinimizer)
        spec        — especificación resuelta (salida de DefinitionResolver)
        output_path — ruta del archivo .java a generar

    Retorna:
        Ruta del archivo generado.
    """
    gen = LexerCodeGenerator(dfa, spec)
    return gen.write(output_path)
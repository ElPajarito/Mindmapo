"""A compact rich-text editor for a node's Intel / Notes.

Supports bold / italic / underline / strikethrough, text + highlight colors,
bullet / numbered lists, an inline "code" style, and live, language-agnostic
syntax highlighting inside code-formatted runs. Content round-trips as HTML.
"""

import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QColor, QFont, QBrush, QTextCharFormat, QTextCursor, QTextListFormat,
    QSyntaxHighlighter, QShortcut, QKeySequence,
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QToolButton, QColorDialog,
)


CODE_FAMILIES = ["Consolas", "DejaVu Sans Mono", "Courier New", "monospace"]


def looks_like_html(s):
    s = (s or "").lower()
    return any(tag in s for tag in ("</", "<p", "<span", "<br", "<html", "<ul", "<ol", "<li"))


def _is_mono(family):
    f = (family or "").lower()
    return any(k in f for k in ("consol", "mono", "courier", "dejavu sans mono"))


class CodeHighlighter(QSyntaxHighlighter):
    """Colorizes tokens, but only inside runs styled with a monospace font."""

    KEYWORDS = [
        # shell / tooling
        "sudo", "chmod", "chown", "curl", "wget", "nmap", "cat", "grep", "cd",
        "ls", "echo", "ssh", "python", "python3", "bash", "sh", "nc", "netcat",
        # general programming
        "def", "class", "return", "import", "from", "if", "else", "elif", "for",
        "while", "try", "except", "finally", "with", "as", "lambda", "yield",
        "pass", "break", "continue", "in", "is", "not", "and", "or", "None",
        "True", "False", "self", "function", "const", "let", "var", "new",
        "await", "async", "public", "private", "static", "void", "int", "char",
        "null", "true", "false", "print", "printf", "echo",
        # sql-ish
        "SELECT", "FROM", "WHERE", "UNION", "INSERT", "UPDATE", "DELETE", "OR",
        "AND",
    ]

    def __init__(self, document):
        super().__init__(document)

        def fmt(color, bold=False, italic=False):
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bold:
                f.setFontWeight(QFont.Bold)
            if italic:
                f.setFontItalic(True)
            return f

        kw = r"\b(" + "|".join(re.escape(k) for k in self.KEYWORDS) + r")\b"
        self.rules = [
            (re.compile(r"\b\d+(\.\d+)?\b"), fmt("#ffd43b")),                 # numbers
            (re.compile(r"\b[A-Za-z_][\w]*(?=\s*\()"), fmt("#74c0fc")),       # calls
            (re.compile(kw), fmt("#ff9d5c", bold=True)),                     # keywords
            (re.compile(r"\"[^\"]*\"|'[^']*'|`[^`]*`"), fmt("#8ce99a")),      # strings
            (re.compile(r"(#|//).*$"), fmt("#6b779c", italic=True)),          # comments
        ]

    def _is_code_block(self, block):
        it = block.begin()
        if it.atEnd():                                   # blank line: follow the one above
            prev = block.previous()
            return prev.isValid() and prev.userState() == 1
        return _is_mono(it.fragment().charFormat().font().family())

    def highlightBlock(self, text):
        if not self._is_code_block(self.currentBlock()):
            self.setCurrentBlockState(0)
            return
        self.setCurrentBlockState(1)
        for pattern, f in self.rules:
            for m in pattern.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), f)


class RichNotesEditor(QWidget):
    """Formatting toolbar + a QTextEdit, emitting `changed` on any edit."""

    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 0, 0)
        bar.setSpacing(3)

        def btn(text, tip, slot, checkable=False):
            b = QToolButton()
            b.setObjectName("fmtBtn")
            b.setText(text)
            b.setToolTip(tip)
            b.setCursor(Qt.PointingHandCursor)
            b.setCheckable(checkable)
            b.clicked.connect(slot)
            bar.addWidget(b)
            return b

        self.b_bold = btn("B", "Bold (Ctrl+B)", self._bold, True)
        self.b_bold.setStyleSheet("font-weight:900;")
        self.b_italic = btn("I", "Italic (Ctrl+I)", self._italic, True)
        self.b_italic.setStyleSheet("font-style:italic;font-weight:800;")
        self.b_underline = btn("U", "Underline (Ctrl+U)", self._underline, True)
        self.b_underline.setStyleSheet("text-decoration:underline;font-weight:800;")
        self.b_strike = btn("S", "Strikethrough", self._strike, True)
        self.b_strike.setStyleSheet("text-decoration:line-through;font-weight:800;")
        btn("\U0001F58D", "Text color", self._color)
        btn("\U0001F58C", "Highlight color", self._highlight)
        self.b_code = btn("</>", "Code / monospace (syntax-highlighted)", self._code, True)
        btn("•", "Bullet list", self._bullet)
        btn("1.", "Numbered list", self._numbered)
        btn("⌧", "Clear formatting", self._clear)
        bar.addStretch(1)
        lay.addLayout(bar)

        self.editor = QTextEdit()
        self.editor.setObjectName("notesEdit")
        self.editor.setAcceptRichText(True)
        self.editor.setPlaceholderText("Creds, ports, payloads, code snippets…")
        self.editor.textChanged.connect(self.changed)
        self.editor.currentCharFormatChanged.connect(self._sync_buttons)
        lay.addWidget(self.editor, 1)

        self.highlighter = CodeHighlighter(self.editor.document())

        for seq, slot in (("Ctrl+B", self._bold), ("Ctrl+I", self._italic),
                          ("Ctrl+U", self._underline)):
            sc = QShortcut(QKeySequence(seq), self.editor)
            sc.activated.connect(slot)

    # ------------------------------------------------------------------ helpers
    def _merge(self, fmt):
        cur = self.editor.textCursor()
        if cur.hasSelection():
            cur.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)
        self.editor.setFocus()

    # ------------------------------------------------------------------ actions
    def _bold(self):
        f = QTextCharFormat()
        on = self.editor.fontWeight() > QFont.Normal
        f.setFontWeight(QFont.Normal if on else QFont.Bold)
        self._merge(f)

    def _italic(self):
        f = QTextCharFormat()
        f.setFontItalic(not self.editor.fontItalic())
        self._merge(f)

    def _underline(self):
        f = QTextCharFormat()
        f.setFontUnderline(not self.editor.fontUnderline())
        self._merge(f)

    def _strike(self):
        f = QTextCharFormat()
        f.setFontStrikeOut(not self.editor.currentCharFormat().fontStrikeOut())
        self._merge(f)

    def _color(self):
        c = QColorDialog.getColor(QColor("#e8edf7"), self, "Text color")
        if c.isValid():
            f = QTextCharFormat()
            f.setForeground(c)
            self._merge(f)

    def _highlight(self):
        c = QColorDialog.getColor(QColor("#FFCC00"), self, "Highlight color")
        if c.isValid():
            f = QTextCharFormat()
            f.setBackground(c)
            self._merge(f)

    def _code(self):
        is_code = _is_mono(self.editor.currentFont().family())
        f = QTextCharFormat()
        if is_code:
            f.setFontFamilies(["Segoe UI"])
            f.setBackground(QBrush(Qt.NoBrush))
            f.setForeground(QColor("#e8edf7"))
        else:
            f.setFontFamilies(CODE_FAMILIES)
            f.setBackground(QColor("#0b1020"))
            f.setForeground(QColor("#d7e0f5"))
        self._merge(f)
        self.highlighter.rehighlight()

    def _bullet(self):
        self.editor.textCursor().createList(QTextListFormat.ListDisc)
        self.editor.setFocus()

    def _numbered(self):
        self.editor.textCursor().createList(QTextListFormat.ListDecimal)
        self.editor.setFocus()

    def _clear(self):
        cur = self.editor.textCursor()
        if not cur.hasSelection():
            cur.select(QTextCursor.BlockUnderCursor)
        base = QTextCharFormat()
        base.setForeground(QColor("#e8edf7"))
        base.setFontFamilies(["Segoe UI"])
        cur.setCharFormat(base)
        self.editor.setCurrentCharFormat(base)
        self.highlighter.rehighlight()
        self.editor.setFocus()

    # ------------------------------------------------------------------ state
    def _sync_buttons(self, fmt):
        self.b_bold.setChecked(self.editor.fontWeight() > QFont.Normal)
        self.b_italic.setChecked(self.editor.fontItalic())
        self.b_underline.setChecked(self.editor.fontUnderline())
        self.b_strike.setChecked(fmt.fontStrikeOut())
        self.b_code.setChecked(_is_mono(self.editor.currentFont().family()))

    # ------------------------------------------------------------------ data
    def set_html(self, content):
        self.editor.blockSignals(True)
        if looks_like_html(content or ""):
            self.editor.setHtml(content)
        else:
            self.editor.setPlainText(content or "")
        self.editor.blockSignals(False)
        self.highlighter.rehighlight()

    def to_html(self):
        return self.editor.toHtml()

    def plain_text(self):
        return self.editor.toPlainText()

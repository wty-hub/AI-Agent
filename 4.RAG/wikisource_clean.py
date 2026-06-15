import re


def _strip_templates(text: str) -> str:
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r"\{\{[^{}]*\}\}", "", text)
    text = re.sub(r"\}\}", "", text)
    text = re.sub(r"\{\{", "", text)
    return text


def _expand_special_templates(text: str) -> str:
    def yl_replace(m: re.Match) -> str:
        if m.group(2):
            return f"{m.group(1)}（{m.group(2)}）"
        return m.group(1)

    text = re.sub(r"\{\{YL\|([^}|]+)(?:\|([^}]+))?\}\}", yl_replace, text)
    text = re.sub(r"\{\{\*\|([^}]+)\}\}", "", text)
    text = re.sub(r"\{\{!\|([^|]+)\|([^}]+)\}\}", r"\2", text)
    text = re.sub(r"\{\{PUA\|([^}]+)\}\}", "", text)
    return text


def _strip_wikilinks(text: str) -> str:
    text = re.sub(r"\[\[(?:[^|\]]+\|)?([^\]]+)\]\]", r"\1", text)
    return text


def _normalize_headings(text: str) -> str:
    text = re.sub(r"^={1,6}\s*(.+?)\s*={1,6}\s*$", r"\1", text, flags=re.M)
    return text


def _strip_markup(text: str) -> str:
    text = re.sub(r"</?onlyinclude>", "", text)
    text = re.sub(r"\[\[Category:[^\]]+\]\]", "", text, flags=re.I)
    text = re.sub(r"^紀\d+\s*$", "", text, flags=re.M)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_header_meta(wikitext: str) -> dict:
    meta = {}
    block = re.search(r"\{\{header\s*\n(.*?)\n\}\}", wikitext, flags=re.S | re.I)
    if block:
        for line in block.group(1).splitlines():
            if "|" not in line or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip().lstrip("|").strip()
            val = _strip_wikilinks(val.strip())
            if key and val:
                meta[key] = val
        return meta

    inline = re.search(r"\{\{Header\|([^}]+)\}\}", wikitext, flags=re.I)
    if inline:
        for part in inline.group(1).split("|"):
            if "=" not in part:
                continue
            key, _, val = part.partition("=")
            if key.strip() and val.strip():
                meta[key.strip()] = val.strip()
    return meta


def clean_wikitext(wikitext: str) -> str:
    text = wikitext
    text = _expand_special_templates(text)
    text = _strip_templates(text)
    text = _strip_wikilinks(text)
    text = _normalize_headings(text)
    text = _strip_markup(text)
    return text

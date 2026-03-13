#!/usr/bin/env python3
"""Structured DOCX extraction using OOXML (Path B).

Goal: produce a stable, semantically richer paragraph stream that matches the
annotation renderer's XML paragraph ordering.

Output includes:
- paragraph_index: index in XML order (.//w:body//w:p)
- text: concatenated w:t
- style_id, style_name
- is_in_table, table_depth
- numbering: numId/ilvl + rendered label if available
- heading_level
- is_heading (derived)
- section_path (derived heading stack)
- clause_number / clause_title (heuristic)
- definitions map (best-effort from Definitions section)

Usage:
  .venv/bin/python scripts/docx_extract_structured.py --in input.docx --out out.yaml
"""

from __future__ import annotations

import argparse
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from lxml import etree
import yaml

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


def qn(local: str) -> str:
    return f"{{{W_NS}}}{local}"


def gettext_p(p: etree._Element) -> str:
    texts = p.xpath(".//w:t/text()", namespaces=NS)
    s = "".join(texts)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def get_p_style(p: etree._Element) -> Tuple[Optional[str], Optional[str]]:
    ppr = p.find("w:pPr", namespaces=NS)
    if ppr is None:
        return None, None
    ps = ppr.find("w:pStyle", namespaces=NS)
    if ps is None:
        return None, None
    style_id = ps.get(qn("val"))
    return style_id, None


def parse_styles(styles_xml: bytes) -> Dict[str, Dict[str, Any]]:
    root = etree.fromstring(styles_xml)
    out: Dict[str, Dict[str, Any]] = {}
    for st in root.xpath(".//w:style", namespaces=NS):
        sid = st.get(qn("styleId"))
        if not sid:
            continue
        name_el = st.find("w:name", namespaces=NS)
        name = name_el.get(qn("val")) if name_el is not None else None
        typ = st.get(qn("type"))
        based = st.find("w:basedOn", namespaces=NS)
        based_on = based.get(qn("val")) if based is not None else None
        outline = None
        ppr = st.find("w:pPr", namespaces=NS)
        if ppr is not None:
            ol = ppr.find("w:outlineLvl", namespaces=NS)
            if ol is not None:
                try:
                    outline = int(ol.get(qn("val")))
                except Exception:
                    outline = None
        out[sid] = {"name": name, "type": typ, "basedOn": based_on, "outlineLvl": outline}
    return out


def get_num_pr(p: etree._Element) -> Tuple[Optional[int], Optional[int]]:
    ppr = p.find("w:pPr", namespaces=NS)
    if ppr is None:
        return None, None
    numpr = ppr.find("w:numPr", namespaces=NS)
    if numpr is None:
        return None, None
    ilvl_el = numpr.find("w:ilvl", namespaces=NS)
    numid_el = numpr.find("w:numId", namespaces=NS)
    ilvl = int(ilvl_el.get(qn("val"))) if ilvl_el is not None and ilvl_el.get(qn("val")) is not None else None
    numid = int(numid_el.get(qn("val"))) if numid_el is not None and numid_el.get(qn("val")) is not None else None
    return numid, ilvl


@dataclass
class NumberingModel:
    num_to_abs: Dict[int, int]
    abs_lvl_text: Dict[int, Dict[int, str]]

    @classmethod
    def from_xml(cls, numbering_xml: Optional[bytes]) -> "NumberingModel":
        if not numbering_xml:
            return cls({}, {})
        root = etree.fromstring(numbering_xml)
        num_to_abs: Dict[int, int] = {}
        for num in root.xpath(".//w:num", namespaces=NS):
            numid = num.get(qn("numId"))
            abs_el = num.find("w:abstractNumId", namespaces=NS)
            if numid is None or abs_el is None or abs_el.get(qn("val")) is None:
                continue
            try:
                num_to_abs[int(numid)] = int(abs_el.get(qn("val")))
            except Exception:
                pass

        abs_lvl_text: Dict[int, Dict[int, str]] = {}
        for absn in root.xpath(".//w:abstractNum", namespaces=NS):
            absid = absn.get(qn("abstractNumId"))
            if absid is None:
                continue
            try:
                absid_i = int(absid)
            except Exception:
                continue
            abs_lvl_text[absid_i] = {}
            for lvl in absn.xpath("./w:lvl", namespaces=NS):
                ilvl = lvl.get(qn("ilvl"))
                lt = lvl.find("w:lvlText", namespaces=NS)
                if ilvl is None or lt is None or lt.get(qn("val")) is None:
                    continue
                try:
                    abs_lvl_text[absid_i][int(ilvl)] = lt.get(qn("val"))
                except Exception:
                    continue

        return cls(num_to_abs=num_to_abs, abs_lvl_text=abs_lvl_text)


class NumberingRenderer:
    def __init__(self, model: NumberingModel):
        self.model = model
        self.counters: Dict[int, Dict[int, int]] = {}

    def _inc(self, numid: int, ilvl: int) -> None:
        self.counters.setdefault(numid, {})
        for k in list(self.counters[numid].keys()):
            if k > ilvl:
                self.counters[numid].pop(k, None)
        self.counters[numid][ilvl] = self.counters[numid].get(ilvl, 0) + 1

    def render(self, numid: Optional[int], ilvl: Optional[int]) -> Optional[str]:
        if numid is None or ilvl is None:
            return None
        self._inc(numid, ilvl)
        absid = self.model.num_to_abs.get(numid)
        if absid is None:
            parts = [str(self.counters[numid].get(l, 0)) for l in range(0, ilvl + 1)]
            return ".".join([p for p in parts if p and p != "0"]) or None

        lvl_text = self.model.abs_lvl_text.get(absid, {}).get(ilvl)
        if not lvl_text:
            parts = [str(self.counters[numid].get(l, 0)) for l in range(0, ilvl + 1)]
            return ".".join([p for p in parts if p and p != "0"]) or None

        out = lvl_text
        for n in range(1, 10):
            val = self.counters[numid].get(n - 1)
            if val is None:
                continue
            out = out.replace(f"%{n}", str(val))
        return out.strip()


def heading_level(style_name: Optional[str]) -> Optional[int]:
    if not style_name:
        return None
    m = re.match(r"Heading\s+(\d+)", style_name)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    return None


def looks_like_clause_heading(text: str, num_label: Optional[str]) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    # Headings should be relatively short.
    if len(t) > 120:
        return False
    # If Word numbering exists, treat as heading-ish.
    if num_label and re.match(r"^\d+(\.\d+)*", num_label):
        return True
    # Regex numbered headings like "7.2 Validity" or "1 Definitions"
    if re.match(r"^\d+(\.\d+)*\s+\S+", t):
        return True
    return False


def parse_clause_number_and_title(text: str, num_label: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    t = (text or "").strip()
    if not t:
        return None, None

    # Prefer computed numbering label
    if num_label and re.match(r"^\d+(\.\d+)*", num_label):
        # If the text already begins with a number, strip it.
        title = re.sub(r"^\d+(\.\d+)*\s+", "", t).strip()
        return num_label, title or None

    m = re.match(r"^(\d+(?:\.\d+)*)\s+(.*)$", t)
    if m:
        return m.group(1), (m.group(2).strip() or None)

    return None, None


def is_definitions_heading(text: str) -> bool:
    t = (text or "").strip().lower()
    return t in {"definitions", "definice"} or t.startswith("definitions") or t.startswith("definice")


def extract_definition_pair(text: str) -> Optional[Tuple[str, str]]:
    """Best-effort extraction of a single definition line.

    Handles:
    - "\"Term\" means ..."
    - "“Term” means ..."
    - "Term: ..."
    """
    t = (text or "").strip()
    if not t:
        return None

    # Quoted term
    m = re.match(r"^[\"“”']?([^\"“”']{2,60})[\"”']\s+(means|shall mean|is|refers to)\s+(.*)$", t, flags=re.I)
    if m:
        term = m.group(1).strip()
        defin = m.group(3).strip()
        return term, defin

    # Term: definition
    m = re.match(r"^([^:]{2,60}):\s+(.*)$", t)
    if m:
        term = m.group(1).strip()
        defin = m.group(2).strip()
        return term, defin

    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    in_path = Path(args.in_path)

    with zipfile.ZipFile(in_path, "r") as z:
        doc_xml = z.read("word/document.xml")
        styles_xml = z.read("word/styles.xml") if "word/styles.xml" in z.namelist() else None
        numbering_xml = z.read("word/numbering.xml") if "word/numbering.xml" in z.namelist() else None

    doc_root = etree.fromstring(doc_xml)
    styles = parse_styles(styles_xml) if styles_xml else {}
    num_model = NumberingModel.from_xml(numbering_xml)
    num_renderer = NumberingRenderer(num_model)

    paragraphs: List[Dict[str, Any]] = []
    ps = doc_root.xpath(".//w:body//w:p", namespaces=NS)

    # heading stack: list of {level:int, title:str}
    heading_stack: List[Dict[str, Any]] = []

    # Definitions section tracking
    in_definitions = False
    definitions_level: Optional[int] = None
    definitions: Dict[str, Dict[str, Any]] = {}

    for idx, p in enumerate(ps):
        text = gettext_p(p)
        sid, _ = get_p_style(p)
        sname = styles.get(sid, {}).get("name") if sid else None
        hlevel = heading_level(sname)
        numid, ilvl = get_num_pr(p)
        num_label = num_renderer.render(numid, ilvl)

        tbl_anc = p.xpath("ancestor::w:tbl", namespaces=NS)
        is_in_table = bool(tbl_anc)
        table_depth = len(tbl_anc)

        # derive heading
        is_heading = False
        if hlevel is not None:
            is_heading = True
        elif looks_like_clause_heading(text, num_label):
            # Guard: avoid treating list items / long sentences as headings
            if ":" in text or text.endswith(":"):
                is_heading = False
            elif len(text.split()) > 8:
                is_heading = False
            else:
                is_heading = True

        clause_no, clause_title = (None, None)
        if is_heading:
            clause_no, clause_title = parse_clause_number_and_title(text, num_label)

        # Maintain heading stack
        if is_heading:
            lvl = hlevel if hlevel is not None else (ilvl + 1 if ilvl is not None else 1)
            # pop to this level
            while heading_stack and heading_stack[-1]["level"] >= lvl:
                heading_stack.pop()
            heading_stack.append({"level": lvl, "title": text})

            # definitions section start
            if is_definitions_heading(text):
                in_definitions = True
                definitions_level = lvl
            else:
                # if we encounter another heading at same/higher level, exit definitions
                if in_definitions and definitions_level is not None and lvl <= definitions_level:
                    in_definitions = False
                    definitions_level = None

        # If we're inside definitions section, try extract term
        if in_definitions and text:
            pair = extract_definition_pair(text)
            if pair:
                term, defin = pair
                # basic cleanup
                term = term.strip().strip("\"“”'")
                if term and defin and term not in definitions:
                    definitions[term] = {"definition": defin, "paragraph_index": idx}

        section_path = [h["title"] for h in heading_stack]

        paragraphs.append({
            "paragraph_index": idx,
            "text": text,
            "style_id": sid,
            "style": sname,
            "is_in_table": is_in_table,
            "table_depth": table_depth,
            "num": {"numId": numid, "ilvl": ilvl, "label": num_label} if numid is not None else None,
            "heading_level": hlevel,
            "is_heading": is_heading,
            "section_path": section_path,
            "clause_number": clause_no,
            "clause_title": clause_title,
        })

    out = {
        "source_file": in_path.name,
        "extraction": {"mode": "ooxml", "paragraph_xpath": ".//w:body//w:p"},
        "paragraphs": paragraphs,
        "definitions": definitions,
    }

    Path(args.out).write_text(yaml.safe_dump(out, sort_keys=False, allow_unicode=True, width=1000), "utf-8")


if __name__ == "__main__":
    main()

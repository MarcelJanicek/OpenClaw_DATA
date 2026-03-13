#!/usr/bin/env python3
"""Annotate a DOCX by inserting Word comments anchored to whole paragraphs.

Why paragraph-level?
- Reliable anchoring without needing fragile character offsets.
- Good enough for pilot: highlights where compliance-relevant content is.

Input:
- Original docx
- Annotations YAML/JSON listing comment(s) for paragraph indices.

Annotation format (YAML):

annotations:
  - paragraph_index: 12
    author: "ComplianceAgent"
    text: "This paragraph appears to define incident reporting. Missing: timeline and portal submission step."

Usage:
  .venv/bin/python scripts/nis2cz_docx_annotate.py \
    --in input.docx \
    --annotations annotations.yaml \
    --out commented.docx

Note:
- Uses OOXML manipulation via zipfile + lxml.
- Creates /word/comments.xml if missing.
- Adds commentRangeStart/End around the paragraph's first run.
"""

from __future__ import annotations

import argparse
import datetime as dt
import zipfile
from pathlib import Path

from lxml import etree
import yaml

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"w": W_NS, "r": R_NS}


def qn(tag: str) -> str:
    prefix, local = tag.split(":", 1)
    if prefix == "w":
        return f"{{{W_NS}}}{local}"
    if prefix == "r":
        return f"{{{R_NS}}}{local}"
    raise ValueError(tag)


def ensure_comments_part(doc_xml: bytes, comments_xml: bytes | None) -> tuple[etree._ElementTree, etree._ElementTree]:
    doc = etree.fromstring(doc_xml)

    if comments_xml is None:
        comments_root = etree.Element(qn("w:comments"), nsmap={"w": W_NS})
        comments = etree.ElementTree(comments_root)
    else:
        comments = etree.ElementTree(etree.fromstring(comments_xml))

    return etree.ElementTree(doc), comments


def next_comment_id(comments_tree: etree._ElementTree) -> int:
    ids = []
    for c in comments_tree.getroot().xpath(".//w:comment", namespaces=NS):
        cid = c.get(qn("w:id"))
        if cid is not None:
            ids.append(int(cid))
    return (max(ids) + 1) if ids else 0


def add_comment(comments_tree: etree._ElementTree, cid: int, author: str, text: str) -> None:
    root = comments_tree.getroot()
    c = etree.SubElement(root, qn("w:comment"))
    c.set(qn("w:id"), str(cid))
    c.set(qn("w:author"), author)
    c.set(qn("w:date"), dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat())

    p = etree.SubElement(c, qn("w:p"))
    r = etree.SubElement(p, qn("w:r"))
    t = etree.SubElement(r, qn("w:t"))
    t.text = text


def anchor_comment_to_paragraph(doc_tree: etree._ElementTree, paragraph_index: int, cid: int) -> bool:
    # NOTE: Must match paragraph ordering used by extraction (python-docx includes
    # paragraphs nested in tables). Use descendant search to include all body
    # paragraphs, not only direct children of w:body.
    paras = doc_tree.getroot().xpath(".//w:body//w:p", namespaces=NS)
    if paragraph_index < 0 or paragraph_index >= len(paras):
        return False

    p = paras[paragraph_index]

    # Find first run; if none, create one.
    runs = p.xpath("./w:r", namespaces=NS)
    if runs:
        r0 = runs[0]
    else:
        r0 = etree.SubElement(p, qn("w:r"))

    # Insert comment range start before first run
    start = etree.Element(qn("w:commentRangeStart"))
    start.set(qn("w:id"), str(cid))
    p.insert(p.index(r0), start)

    # Insert comment range end after last element in paragraph
    end = etree.Element(qn("w:commentRangeEnd"))
    end.set(qn("w:id"), str(cid))
    p.append(end)

    # Add comment reference run (required)
    ref_run = etree.SubElement(p, qn("w:r"))
    rpr = etree.SubElement(ref_run, qn("w:rPr"))
    etree.SubElement(rpr, qn("w:rStyle")).set(qn("w:val"), "CommentReference")
    cref = etree.SubElement(ref_run, qn("w:commentReference"))
    cref.set(qn("w:id"), str(cid))

    return True


def ensure_document_rels(rels_xml: bytes | None) -> etree._ElementTree:
    if rels_xml is None:
        root = etree.Element("Relationships", nsmap={None: PKG_REL_NS})
        return etree.ElementTree(root)
    return etree.ElementTree(etree.fromstring(rels_xml))


def add_comments_relationship(rels_tree: etree._ElementTree) -> None:
    root = rels_tree.getroot()
    # check existing
    for rel in root.findall(f"{{{PKG_REL_NS}}}Relationship"):
        if rel.get("Type") == "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments":
            return

    # generate new id
    rids = []
    for rel in root.findall(f"{{{PKG_REL_NS}}}Relationship"):
        rid = rel.get("Id", "")
        if rid.startswith("rId"):
            try:
                rids.append(int(rid[3:]))
            except ValueError:
                pass
    next_id = (max(rids) + 1) if rids else 1

    rel = etree.SubElement(root, f"{{{PKG_REL_NS}}}Relationship")
    rel.set("Id", f"rId{next_id}")
    rel.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments")
    rel.set("Target", "comments.xml")


def ensure_content_types(ct_xml: bytes) -> etree._ElementTree:
    return etree.ElementTree(etree.fromstring(ct_xml))


def ensure_comments_content_type(ct_tree: etree._ElementTree) -> None:
    root = ct_tree.getroot()
    # look for Override PartName="/word/comments.xml"
    for ov in root.findall("{http://schemas.openxmlformats.org/package/2006/content-types}Override"):
        if ov.get("PartName") == "/word/comments.xml":
            return

    ov = etree.SubElement(root, "{http://schemas.openxmlformats.org/package/2006/content-types}Override")
    ov.set("PartName", "/word/comments.xml")
    ov.set("ContentType", "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True)
    ap.add_argument("--annotations", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    ann = yaml.safe_load(Path(args.annotations).read_text("utf-8"))
    annotations = ann.get("annotations", ann)

    in_path = Path(args.in_path)
    out_path = Path(args.out)

    with zipfile.ZipFile(in_path, "r") as zin:
        files = {name: zin.read(name) for name in zin.namelist()}

    doc_xml = files["word/document.xml"]
    comments_xml = files.get("word/comments.xml")
    rels_xml = files.get("word/_rels/document.xml.rels")
    ct_xml = files["[Content_Types].xml"]

    doc_tree, comments_tree = ensure_comments_part(doc_xml, comments_xml)

    cid = next_comment_id(comments_tree)

    for a in annotations:
        pidx = int(a["paragraph_index"])
        author = a.get("author", "ComplianceAgent")
        text = a["text"]

        ok = anchor_comment_to_paragraph(doc_tree, pidx, cid)
        if not ok:
            continue
        add_comment(comments_tree, cid, author, text)
        cid += 1

    rels_tree = ensure_document_rels(rels_xml)
    add_comments_relationship(rels_tree)

    ct_tree = ensure_content_types(ct_xml)
    ensure_comments_content_type(ct_tree)

    # Write new docx
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            if name == "word/document.xml":
                data = etree.tostring(doc_tree.getroot(), xml_declaration=True, encoding="UTF-8", standalone="yes")
            elif name == "word/comments.xml":
                data = etree.tostring(comments_tree.getroot(), xml_declaration=True, encoding="UTF-8", standalone="yes")
            elif name == "word/_rels/document.xml.rels":
                data = etree.tostring(rels_tree.getroot(), xml_declaration=True, encoding="UTF-8", standalone="yes")
            elif name == "[Content_Types].xml":
                data = etree.tostring(ct_tree.getroot(), xml_declaration=True, encoding="UTF-8", standalone="yes")
            zout.writestr(name, data)

        # Add missing parts if they didn't exist
        if "word/comments.xml" not in files:
            data = etree.tostring(comments_tree.getroot(), xml_declaration=True, encoding="UTF-8", standalone="yes")
            zout.writestr("word/comments.xml", data)
        if "word/_rels/document.xml.rels" not in files:
            data = etree.tostring(rels_tree.getroot(), xml_declaration=True, encoding="UTF-8", standalone="yes")
            zout.writestr("word/_rels/document.xml.rels", data)


if __name__ == "__main__":
    main()

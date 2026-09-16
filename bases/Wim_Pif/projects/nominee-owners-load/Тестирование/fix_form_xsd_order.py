#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Put stretch/height properties before DataPath so Designer XDTO accepts Form.xml."""

from lxml import etree

FORM_XML = r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Pif\projects\nominee-owners-load\src\ЗаполнениеСпискаВладельцевНД\Forms\Форма\Ext\Form.xml"
NS = "http://v8.1c.ru/8.3/xcf/logform"


def q(name):
    return "{%s}%s" % (NS, name)


def local(tag):
    return tag.split("}")[-1] if isinstance(tag, str) else tag


def make(name, text):
    el = etree.Element(q(name))
    el.text = text
    return el


def find_child(parent, name):
    for child in parent:
        if local(child.tag) == name:
            return child
    return None


def insert_before_datapath_or_companions(parent, el):
    for i, child in enumerate(list(parent)):
        n = local(child.tag)
        if n in (
            "DataPath", "RowFilter", "ContextMenu", "AutoCommandBar",
            "ExtendedTooltip", "SearchStringAddition", "ViewStatusAddition",
            "SearchControlAddition", "Events", "ChildItems",
        ):
            parent.insert(i, el)
            return
    parent.append(el)


def take_or_make(parent, name, text):
    existing = find_child(parent, name)
    if existing is not None:
        parent.remove(existing)
        existing.text = text
        return existing
    return make(name, text)


def patch_table(table):
    height = find_child(table, "HeightInTableRows")
    height_text = height.text if height is not None else "18"
    if height is not None:
        table.remove(height)
    for name, text in (
        ("AutoMaxWidth", "false"),
        ("AutoMaxHeight", "false"),
        ("HorizontalStretch", "true"),
        ("VerticalStretch", "true"),
        ("HeightInTableRows", height_text),
    ):
        insert_before_datapath_or_companions(table, take_or_make(table, name, text))


def insert_after_pages_repr(pages, el):
    for i, child in enumerate(list(pages)):
        if local(child.tag) == "PagesRepresentation":
            pages.insert(i + 1, el)
            return
    for i, child in enumerate(list(pages)):
        if local(child.tag) in ("ExtendedTooltip", "Events", "ChildItems"):
            pages.insert(i, el)
            return
    pages.append(el)


def patch_pages(pages):
    for name in ("AutoMaxWidth", "HorizontalStretch", "VerticalStretch"):
        el = find_child(pages, name)
        if el is not None:
            pages.remove(el)
    repr_el = find_child(pages, "PagesRepresentation")
    if repr_el is not None:
        idx = list(pages).index(repr_el)
        pages.insert(idx, make("VerticalStretch", "true"))
        pages.insert(idx, make("HorizontalStretch", "true"))
        pages.insert(idx, make("AutoMaxWidth", "false"))
        return
    for i, child in enumerate(list(pages)):
        if local(child.tag) in ("ExtendedTooltip", "Events", "ChildItems"):
            pages.insert(i, make("VerticalStretch", "true"))
            pages.insert(i, make("HorizontalStretch", "true"))
            pages.insert(i, make("AutoMaxWidth", "false"))
            return


def patch_page(page):
    for name in ("AutoMaxWidth", "HorizontalStretch", "VerticalStretch"):
        el = find_child(page, name)
        if el is not None:
            page.remove(el)
    group_el = find_child(page, "Group")
    if group_el is not None:
        idx = list(page).index(group_el)
        page.insert(idx, make("VerticalStretch", "true"))
        page.insert(idx, make("HorizontalStretch", "true"))
        page.insert(idx, make("AutoMaxWidth", "false"))
        return
    for i, child in enumerate(list(page)):
        if local(child.tag) in ("ExtendedTooltip", "Events", "ChildItems"):
            page.insert(i, make("VerticalStretch", "true"))
            page.insert(i, make("HorizontalStretch", "true"))
            page.insert(i, make("AutoMaxWidth", "false"))
            return


def patch_form(root):
    return


def main():
    tree = etree.parse(FORM_XML)
    root = tree.getroot()
    patch_form(root)
    for el in root.iter():
        name = local(el.tag)
        if name == "Table":
            patch_table(el)
        elif name == "Pages":
            patch_pages(el)
        elif name == "Page":
            patch_page(el)
    tree.write(FORM_XML, encoding="UTF-8", xml_declaration=True, pretty_print=True)
    print("OK patched Form.xml")


if __name__ == "__main__":
    main()

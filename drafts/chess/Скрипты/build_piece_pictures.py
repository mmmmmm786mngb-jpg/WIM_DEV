#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Рисует фигуры и упаковывает их в общие картинки расширения.
"""

import io
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(r"c:\1c\Cursor_1c\WIM_DEV\drafts\chess\cfe\CommonPictures")
SCALE = 4
SIZE = 256

PIECES = [
    "Шахматы_БелаяПешка",
    "Шахматы_БелыйКонь",
    "Шахматы_БелыйСлон",
    "Шахматы_БелаяЛадья",
    "Шахматы_БелыйФерзь",
    "Шахматы_БелыйКороль",
    "Шахматы_ЧернаяПешка",
    "Шахматы_ЧерныйКонь",
    "Шахматы_ЧерныйСлон",
    "Шахматы_ЧернаяЛадья",
    "Шахматы_ЧерныйФерзь",
    "Шахматы_ЧерныйКороль",
]


def sx(value):
    return int(value * SCALE)


def point(x, y):
    return (sx(x), sx(y))


def colors(white):
    if white:
        return (248, 244, 236, 255), (42, 36, 32, 255)
    return (54, 48, 44, 255), (236, 226, 210, 255)


def base(draw, fill, outline, width):
    draw.rounded_rectangle(
        [sx(78), sx(214), sx(178), sx(238)],
        radius=sx(8),
        fill=fill,
        outline=outline,
        width=width,
    )
    draw.polygon(
        [point(96, 188), point(160, 188), point(176, 220), point(80, 220)],
        fill=fill,
    )
    draw.line(
        [point(96, 188), point(80, 220), point(176, 220), point(160, 188)],
        fill=outline,
        width=width,
    )


def pawn(draw, fill, outline, width):
    base(draw, fill, outline, width)
    draw.polygon(
        [point(114, 118), point(142, 118), point(136, 200), point(120, 200)],
        fill=fill,
    )
    draw.line(
        [point(114, 118), point(120, 200), point(136, 200), point(142, 118)],
        fill=outline,
        width=width,
    )
    draw.ellipse([sx(100), sx(70), sx(156), sx(134)], fill=fill, outline=outline, width=width)


def rook(draw, fill, outline, width):
    base(draw, fill, outline, width)
    draw.rectangle([sx(96), sx(108), sx(160), sx(204)], fill=fill, outline=outline, width=width)
    battlements = [88, 112, 136, 160]
    for left in battlements:
        draw.rectangle(
            [sx(left), sx(72), sx(left + 20), sx(114)],
            fill=fill,
            outline=outline,
            width=width,
        )


def knight(draw, fill, outline, width, face_right):
    base(draw, fill, outline, width)
    raw = [
        (118, 48),
        (104, 78),
        (128, 70),
        (156, 96),
        (172, 128),
        (158, 138),
        (146, 124),
        (138, 156),
        (164, 186),
        (150, 206),
        (104, 206),
        (108, 168),
        (86, 184),
        (74, 150),
        (92, 132),
        (86, 96),
        (104, 84),
    ]
    if face_right:
        pts = [point(x, y) for x, y in raw]
    else:
        pts = [point(256 - x, y) for x, y in raw]
    draw.polygon(pts, fill=fill)
    draw.line(pts + [pts[0]], fill=outline, width=width, joint="curve")
    eye = (148, 108) if face_right else (108, 108)
    radius = sx(5)
    center = point(*eye)
    draw.ellipse(
        [center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius],
        fill=outline,
    )


def bishop(draw, fill, outline, width):
    base(draw, fill, outline, width)
    draw.polygon(
        [point(128, 58), point(156, 132), point(146, 204), point(110, 204), point(100, 132)],
        fill=fill,
    )
    draw.line(
        [
            point(128, 58),
            point(156, 132),
            point(146, 204),
            point(110, 204),
            point(100, 132),
            point(128, 58),
        ],
        fill=outline,
        width=width,
    )
    draw.line([point(128, 86), point(128, 118)], fill=outline, width=width)


def queen(draw, fill, outline, width):
    base(draw, fill, outline, width)
    draw.polygon(
        [point(108, 132), point(148, 132), point(158, 204), point(98, 204)],
        fill=fill,
        outline=outline,
    )
    draw.line(
        [point(108, 132), point(98, 204), point(158, 204), point(148, 132)],
        fill=outline,
        width=width,
    )
    tips = [84, 106, 128, 150, 172]
    for tip in tips:
        draw.line([point(tip, 78), point(128, 136)], fill=outline, width=max(width - 4, 2))
        draw.ellipse(
            [sx(tip - 10), sx(62), sx(tip + 10), sx(86)],
            fill=fill,
            outline=outline,
            width=width,
        )


def king(draw, fill, outline, width):
    queen(draw, fill, outline, width)
    draw.rectangle([sx(120), sx(28), sx(136), sx(68)], fill=fill, outline=outline, width=width)
    draw.rectangle([sx(106), sx(42), sx(150), sx(56)], fill=fill, outline=outline, width=width)


def draw_piece(name):
    white = "Белая" in name or "Белый" in name
    fill, outline = colors(white)
    image = Image.new("RGBA", (sx(SIZE), sx(SIZE)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    width = sx(7)
    if name.endswith("Пешка"):
        pawn(draw, fill, outline, width)
    elif name.endswith("Конь"):
        knight(draw, fill, outline, width, white)
    elif name.endswith("Слон"):
        bishop(draw, fill, outline, width)
    elif name.endswith("Ладья"):
        rook(draw, fill, outline, width)
    elif name.endswith("Ферзь"):
        queen(draw, fill, outline, width)
    else:
        king(draw, fill, outline, width)
    return image.resize((SIZE, SIZE), Image.Resampling.LANCZOS)


def manifest(variants):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<Picture>",
    ]
    for file_name, density, side in variants:
        lines.append(
            '\t<PictureVariant name="%s" screenDensity="%s" glyphWidth="%s" glyphHeight="%s"/>'
            % (file_name, density, side, side)
        )
    lines.append(
        '\t<PictureVariant name="Picture.png" interfaceVariant="version8_2" '
        'screenDensity="ldpi" glyphWidth="256" glyphHeight="256"/>'
    )
    lines.append("</Picture>")
    return "\n".join(lines)


def png_bytes(image, side):
    scaled = image.resize((side, side), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    scaled.save(buffer, format="PNG")
    return buffer.getvalue()


def write_picture(name, image):
    folder = ROOT / name / "Ext" / "Picture"
    folder.mkdir(parents=True, exist_ok=True)
    variants = [
        ("85.png", "bldpi", 64),
        ("100.png", "ldpi", 96),
        ("125.png", "aldpi", 112),
        ("150.png", "mdpi", 128),
        ("175.png", "amdpi", 144),
        ("200.png", "hdpi", 160),
        ("300.png", "xdpi", 192),
        ("400.png", "udpi", 256),
    ]
    archive_path = folder / "Picture.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.xml", manifest(variants))
        archive.writestr("Picture.png", png_bytes(image, SIZE))
        for file_name, _density, side in variants:
            archive.writestr(file_name, png_bytes(image, side))
    picture_xml = folder.parent / "Picture.xml"
    picture_xml.write_text(
        "\n".join(
            [
                '<?xml version="1.0" encoding="UTF-8"?>',
                '<ExtPicture xmlns="http://v8.1c.ru/8.3/xcf/extrnprops" '
                'xmlns:xr="http://v8.1c.ru/8.3/xcf/readable" '
                'xmlns:xs="http://www.w3.org/2001/XMLSchema" '
                'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.20">',
                "\t<Picture>",
                "\t\t<xr:Abs>Picture.zip</xr:Abs>",
                "\t\t<xr:LoadTransparent>true</xr:LoadTransparent>",
                "\t</Picture>",
                "</ExtPicture>",
                "",
            ]
        ),
        encoding="utf-8",
    )
    preview = ROOT.parent / "piece-preview" / (name + ".png")
    preview.parent.mkdir(parents=True, exist_ok=True)
    image.save(preview)


def main():
    for name in PIECES:
        write_picture(name, draw_piece(name))
        print(name)


if __name__ == "__main__":
    main()

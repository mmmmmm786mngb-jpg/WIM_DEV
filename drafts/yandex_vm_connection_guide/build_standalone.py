#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild both standalone HTML guides with embedded assets."""

import base64
from pathlib import Path

base = Path(r"c:\1c\Cursor_1c\WIM_DEV\drafts\yandex_vm_connection_guide")
drafts = Path(r"c:\1c\Cursor_1c\WIM_DEV\drafts")

images = [
    "images/vim_logo.png",
    "images/step1_it_portal.png",
    "images/step2_search_pam.png",
    "images/step3_pam_login.png",
    "images/step5_rdp_auth.png",
    "images/step6_vm_credentials.png",
    "images/olga_mremoteng_config.png",
    "images/olga_rdp_shortcut.png",
    "images/olga_rdp_notepad.png",
]


def embed(html: str) -> str:
    for rel in images:
        path = base / rel
        if not path.exists():
            print("MISSING", rel)
            continue
        uri = "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")
        html = html.replace('src="' + rel + '"', 'src="' + uri + '"')
        html = html.replace('href="' + rel + '"', 'href="' + uri + '"')
    rdp = base / "VM_Yandex_1.rdp"
    if rdp.exists():
        rdp_uri = "data:application/rdp;base64," + base64.b64encode(rdp.read_bytes()).decode("ascii")
        html = html.replace('href="VM_Yandex_1.rdp"', 'href="' + rdp_uri + '"')
    return html


# Classic guide
classic = embed((base / "index.html").read_text(encoding="utf-8"))
(base / "yandex_vm_connection_guide_standalone.html").write_text(classic, encoding="utf-8")
(drafts / "kak_podklyuchitsya_k_yandex_vm.html").write_text(classic, encoding="utf-8")
print("classic", round(len(classic.encode("utf-8")) / 1024, 1), "KB")

# Mission guide
mission = embed((base / "mission_control.html").read_text(encoding="utf-8"))
(drafts / "kak_podklyuchitsya_k_yandex_vm_mission.html").write_text(mission, encoding="utf-8")
print("mission", round(len(mission.encode("utf-8")) / 1024, 1), "KB")
print("ext classic", classic.count('src="images/'))
print("ext mission", mission.count('src="images/'))

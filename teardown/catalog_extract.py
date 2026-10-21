"""Decode G*Power's UI text from a REA `inspect_pe_resources` result.

REA gives the exact file range of every resource payload; this script reads those
ranges from the exe (no execution) and decodes dialogs, menus and string tables
into JSON, which is what the teardown report and coverage matrix are built from.

usage: python -I teardown/catalog_extract.py <rea_result.json> <GPowerNT.exe> <out.json>
"""
import json
import re
import struct
import sys

RT = {2: "bitmap", 3: "icon", 4: "menu", 5: "dialog", 6: "string", 9: "accelerator",
      14: "group_icon", 16: "version", 24: "manifest", 240: "dlginit", 241: "toolbar"}

UTF16_RUN = re.compile(rb"(?:[\x20-\x7e\xa0-\xff]\x00){2,}")


def utf16_runs(blob):
    return [m.group().decode("utf-16-le") for m in UTF16_RUN.finditer(blob)]


def string_table(block_id, blob):
    # Block n holds string ids (n-1)*16 .. (n-1)*16+15, each length-prefixed UTF-16.
    out, pos = {}, 0
    for i in range(16):
        if pos + 2 > len(blob):
            break
        (n,) = struct.unpack_from("<H", blob, pos)
        pos += 2
        if n:
            out[(block_id - 1) * 16 + i] = blob[pos:pos + 2 * n].decode("utf-16-le", "replace")
            pos += 2 * n
    return out


def main(rea_path, exe_path, out_path):
    rea = json.load(open(rea_path, encoding="utf-8"))
    exe = open(exe_path, "rb").read()
    result = {"source_sha256": rea["subject"].get("digest"), "dialogs": [], "menus": [],
              "strings": {}, "resource_counts": {}}
    for res in rea["normalized_result"]["resources"]:
        tid = res["type"].get("id")
        kind = RT.get(tid, f"type_{tid}")
        result["resource_counts"][kind] = result["resource_counts"].get(kind, 0) + 1
        loc = res["payload"]["location"]
        blob = exe[loc["offset"]:loc["offset"] + loc["bytes"]]
        name = res["name"].get("id", res["name"].get("name"))
        if kind == "dialog":
            texts = utf16_runs(blob)
            result["dialogs"].append({"id": name, "texts": texts})
        elif kind == "menu":
            result["menus"].append({"id": name, "items": utf16_runs(blob)})
        elif kind == "string":
            result["strings"].update({str(k): v for k, v in string_table(name, blob).items()})
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: (len(v) if isinstance(v, (list, dict)) else v)
                      for k, v in result.items() if k != "source_sha256"}))


if __name__ == "__main__":
    main(*sys.argv[1:4])

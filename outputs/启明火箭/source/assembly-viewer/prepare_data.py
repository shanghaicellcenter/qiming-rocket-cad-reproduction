from pathlib import Path
import json
import hashlib
import struct
import os

HERE = Path(__file__).resolve().parent
BASE = Path(os.environ.get("MACHINE_METADATA_BASE", HERE.parents[1] / "native-cad")).resolve()

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def glb_info(path):
    with path.open("rb") as f:
        head = f.read(20)
        if head[:4] != b"glTF":
            raise ValueError(f"Not GLB: {path}")
        length, kind = struct.unpack_from("<II", head, 12)
        if kind != 0x4E4F534A:
            raise ValueError("GLB JSON chunk is missing")
        doc = json.loads(f.read(length))
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    roots = [doc['nodes'][i].get('extras', {}) for scene in doc.get('scenes', []) for i in scene.get('nodes', [])]
    return {"bytes": path.stat().st_size, "sha256": digest.hexdigest(),
            "glb_nodes": len(doc.get("nodes", [])),
            "glb_mesh_definitions": len(doc.get("meshes", [])),
            "generator": doc.get("asset", {}).get("generator"), "root_identities": roots}

config = read(HERE / "assets.json")
name_map = read(BASE / "vehicle.name-source-map.json")
hierarchy = read(BASE / "vehicle.hierarchy.json")
full_validation = read(BASE / "vehicle.validation.json")
labels = read(BASE / "component-labels.json")
assembly_map = read(BASE / "source-assembly-map.json")

assets = []
for group in ["models", "library"]:
    for raw in config.get(group, []):
        path = (HERE / raw["path"]).resolve()
        if not path.is_file():
            continue
        meta = {k: v for k, v in raw.items() if k not in {"path", "audit", "validation"}}
        meta.update(glb_info(path))
        meta.update({"asset_id": "model-" + raw["id"], "kind": "assembly" if group == "models" else "library", "development_uri": raw['path']})
        val = (HERE / raw.get("validation", "not-available")).resolve()
        if val.is_file():
            v = read(val)
            meta["validation_summary"] = {k: v.get(k) for k in ["mesh_count", "face_count", "meters_per_unit", "up_axis", "sha256"]}
        assets.append(meta)

prims = []
for p in hierarchy["prims"]:
    if p["path"].startswith("/vehicle/vehicle") and p.get("type") in {"Xform", "Mesh"}:
        prims.append({k: p.get(k) for k in ["path", "parent", "name", "display_name", "type", "kind", "visible"]})

provider = {}
for m in full_validation.get("meshes", []):
    provider[m["path"]] = {
        "source_full_faces": m.get("faces"),
        "point_attribute_providers": m.get("point_attribute_providers", []),
    }

source = {
    "entry": assembly_map["primary_vehicle_assembly_candidate"]["filename"],
    "archive": assembly_map["source_release_structure"]["main_cad_archive"],
    "archive_sha256": name_map["source_zip_sha256"],
    "source_file_count": name_map["source_cad_files"],
    "source_part_file_count": name_map["source_parts"],
    "source_assembly_file_count": name_map["source_assemblies"],
    "matched_source_files": name_map["distinct_source_files_with_unique_name_match"],
    "matched_source_nodes": name_map["nodes_with_unique_name_match"],
    "unmatched_source_files": name_map["source_files_not_name_matched"],
    "match_limits": name_map["limits"],
    "source_unit_metres": full_validation["meters_per_unit"],
    "source_up_axis": full_validation["up_axis"],
    "source_full_mesh_count": full_validation["mesh_count"],
    "source_full_triangles": full_validation["face_count"],
    "source_usd_sha256": full_validation["sha256"],
    "source_unique_point_providers": full_validation["unique_point_attribute_provider_count"],
}
library_entries = []
for a in assets:
    if a['kind'] != 'library':
        continue
    for identity in a.get('root_identities', []):
        if identity.get('supplement_id'):
            library_entries.append({'asset_id': a['id'], **identity})
exports = {"ASSETS": assets, "SOURCE": source, "SOURCE_NODES": name_map["nodes"],
           "SOURCE_PRIMS": prims, "PROVIDERS": provider, "LABELS": labels["by_basename"],
           "PATCH_LABELS": labels['independent_patch_records'], "LIBRARY_ENTRIES": library_entries,
           "SOURCE_CATALOG": assembly_map["native_source_catalog"]}
destination = HERE / "source" / "data.js"
destination.write_text("\n".join("export const " + k + "=" + json.dumps(v, ensure_ascii=False, separators=(",", ":")) + ";" for k, v in exports.items()) + "\n", encoding="utf-8")
# Presentation naming is deliberately separate from the exact source catalog,
# filenames, identifiers and hash fields written above.
(HERE / "source" / "public-project.js").write_text(
    'export const PUBLIC_PROJECT_NAME="启明火箭";\n', encoding="utf-8")
print(json.dumps({"metadata": str(destination), "available_assets": [a["id"] for a in assets]}, ensure_ascii=False))

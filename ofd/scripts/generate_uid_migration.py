"""
Generate UID Migration Script.

Produces a mapping from the previous (name-derived) entity UUIDs to the new
(id-derived) entity UUIDs after the filament UUID-derivation switch in
ofd/builder/crawler.py.

The filament UUID derivation changed from `generate_filament_id(brand, material, NAME)`
to `generate_filament_id(brand, material, ID)`. That change cascades into every
downstream entity whose UUID is derived from the filament UUID:

  - filament
  - variant   (variant_id is derived from filament_id + variant.id)
  - size      (size_id is derived from variant_id + size fields)
  - purchase_link (pl_id is derived from size_id + store_id + url)

Brand, material, and store UUIDs are unchanged.

Output is a single JSON file with two top-level keys:
  - `mapping`: a flat `{old_uid: new_uid}` dictionary
  - `old_filament_collisions`: list of cases where multiple filament folders
    shared the same old UUID (omitted when there are none)

Usage:
    ofd script generate_uid_migration
    ofd script generate_uid_migration --output uid_migration.json
    ofd script generate_uid_migration --csv uid_migration.csv
"""

import argparse
import csv
import json
from pathlib import Path

from ofd.base import BaseScript, ScriptResult, register_script
from ofd.builder.utils import (
    generate_brand_id,
    generate_filament_id,
    generate_material_id,
    generate_purchase_link_id,
    generate_size_id,
    generate_store_id,
    generate_variant_id,
)


@register_script
class GenerateUidMigrationScript(BaseScript):
    name = "generate_uid_migration"
    description = (
        "Generate a flat {old_uid: new_uid} mapping for entities whose UUIDs "
        "changed when filament UUID derivation switched from name to id."
    )

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--output",
            "-o",
            default="uid_migration.json",
            help="Path to write the JSON mapping (default: uid_migration.json)",
        )
        parser.add_argument(
            "--csv",
            metavar="PATH",
            help="Also write a flat CSV with columns old_id,new_id",
        )
        parser.add_argument(
            "--data-dir",
            default=None,
            help="Override data directory (default: project_root/data)",
        )
        parser.add_argument(
            "--stores-dir",
            default=None,
            help="Override stores directory (default: project_root/stores)",
        )

    def run(self, args: argparse.Namespace) -> ScriptResult:
        data_dir = Path(args.data_dir) if args.data_dir else self.data_dir
        stores_dir = Path(args.stores_dir) if args.stores_dir else self.stores_dir

        if not data_dir.exists():
            return ScriptResult(success=False, message=f"Data directory not found: {data_dir}")
        if not stores_dir.exists():
            return ScriptResult(success=False, message=f"Stores directory not found: {stores_dir}")

        store_uuid_by_source_id = self._build_store_uuid_index(stores_dir)

        mapping: dict[str, str] = {}
        old_filament_collisions: dict[str, list[str]] = {}

        for brand_dir in sorted(data_dir.iterdir()):
            if not brand_dir.is_dir() or brand_dir.name.startswith("."):
                continue
            brand_id = generate_brand_id(brand_dir.name)

            for material_dir in sorted(brand_dir.iterdir()):
                if not material_dir.is_dir() or material_dir.name.startswith("."):
                    continue
                material_id = generate_material_id(brand_id, material_dir.name)

                for filament_dir in sorted(material_dir.iterdir()):
                    if not filament_dir.is_dir() or filament_dir.name.startswith("."):
                        continue
                    filament_json = filament_dir / "filament.json"
                    if not filament_json.exists():
                        continue
                    try:
                        filament_data = json.loads(filament_json.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        continue

                    filament_source_id = filament_data.get("id", filament_dir.name)
                    filament_name = filament_data.get("name", filament_dir.name)

                    old_fid = generate_filament_id(brand_id, material_id, filament_name)
                    new_fid = generate_filament_id(brand_id, material_id, filament_source_id)

                    old_filament_collisions.setdefault(old_fid, []).append(
                        f"{brand_dir.name}/{material_dir.name}/{filament_dir.name}"
                    )

                    if old_fid != new_fid:
                        mapping[old_fid] = new_fid

                    for variant_dir in sorted(filament_dir.iterdir()):
                        if not variant_dir.is_dir() or variant_dir.name.startswith("."):
                            continue
                        variant_json = variant_dir / "variant.json"
                        if not variant_json.exists():
                            continue
                        try:
                            variant_data = json.loads(variant_json.read_text(encoding="utf-8"))
                        except (OSError, json.JSONDecodeError):
                            continue

                        variant_source_id = variant_data.get("id", variant_dir.name)
                        old_vid = generate_variant_id(old_fid, variant_source_id)
                        new_vid = generate_variant_id(new_fid, variant_source_id)
                        if old_vid != new_vid:
                            mapping[old_vid] = new_vid

                        sizes_json = variant_dir / "sizes.json"
                        if not sizes_json.exists():
                            continue
                        try:
                            sizes_data = json.loads(sizes_json.read_text(encoding="utf-8"))
                        except (OSError, json.JSONDecodeError):
                            continue
                        if not isinstance(sizes_data, list):
                            sizes_data = [sizes_data]

                        for idx, size_entry in enumerate(sizes_data):
                            if not isinstance(size_entry, dict):
                                continue
                            if size_entry.get("filament_weight") is None:
                                continue

                            old_sid = generate_size_id(old_vid, size_entry, idx)
                            new_sid = generate_size_id(new_vid, size_entry, idx)
                            if old_sid != new_sid:
                                mapping[old_sid] = new_sid

                            for pl_entry in size_entry.get("purchase_links") or []:
                                if not isinstance(pl_entry, dict):
                                    continue
                                source_store_id = pl_entry.get("store_id")
                                url = pl_entry.get("url")
                                if not source_store_id or not url:
                                    continue
                                store_uuid = store_uuid_by_source_id.get(source_store_id)
                                if not store_uuid:
                                    continue

                                old_plid = generate_purchase_link_id(old_sid, store_uuid, url)
                                new_plid = generate_purchase_link_id(new_sid, store_uuid, url)
                                if old_plid != new_plid:
                                    mapping[old_plid] = new_plid

        collisions = [
            {"old_id": old_fid, "locations": sorted(locs)}
            for old_fid, locs in sorted(old_filament_collisions.items())
            if len(locs) > 1
        ]

        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = self.project_root / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        payload: dict = {"mapping": mapping}
        if collisions:
            payload["old_filament_collisions"] = collisions

        output_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

        csv_path: Path | None = None
        if args.csv:
            csv_path = Path(args.csv)
            if not csv_path.is_absolute():
                csv_path = self.project_root / csv_path
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            with csv_path.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(["old_id", "new_id"])
                for old_id, new_id in mapping.items():
                    writer.writerow([old_id, new_id])

        if not self.json_mode:
            print(f"Wrote {len(mapping):,} mappings to {output_path}")
            if csv_path:
                print(f"Wrote CSV to {csv_path}")
            if collisions:
                print(
                    f"WARNING: {len(collisions)} old filament UUID(s) "
                    "collided across multiple folders — see "
                    "`old_filament_collisions` in the JSON output"
                )

        return ScriptResult(
            success=True,
            message=f"Generated {len(mapping)} UID mappings",
            data={
                "output": str(output_path),
                "csv": str(csv_path) if csv_path else None,
                "count": len(mapping),
                "collision_count": len(collisions),
            },
        )

    def _build_store_uuid_index(self, stores_dir: Path) -> dict[str, str]:
        """Map source store id (from store.json) -> derived store UUID."""
        index: dict[str, str] = {}
        for store_dir in sorted(stores_dir.iterdir()):
            if not store_dir.is_dir() or store_dir.name.startswith("."):
                continue
            store_json = store_dir / "store.json"
            if not store_json.exists():
                continue
            try:
                data = json.loads(store_json.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            source_id = data.get("id")
            if not source_id:
                continue
            index[source_id] = generate_store_id(source_id)
        return index

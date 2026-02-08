#!/usr/bin/env python3
"""
Fix filament subtype naming by splitting mixed product lines into separate subtypes.

For each move rule:
1. Creates the target subtype directory
2. Creates a filament.json (copied from source, with updated id/name)
3. Moves matching variant directories (stripping the product-line prefix)
4. Updates variant.json (id and name)

Usage:
  python scripts/fix_subtype_naming.py --dry-run     # Preview all changes
  python scripts/fix_subtype_naming.py               # Apply changes
  python scripts/fix_subtype_naming.py --delete-dupes # Delete source when target exists
"""

import json
import shutil
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Each move rule defines:
#   manufacturer, material, source_subtype, id_prefix, name_prefix,
#   target_subtype, target_display_name
#
# name_prefix: the exact string at the start of variant.json "name" to strip.
#   Use a list of alternatives if the prefix varies across variants.
MOVE_RULES = [
    # =========================================================================
    # 3djake PLA
    # =========================================================================
    {
        "manufacturer": "3djake",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "eco_",
        "name_prefix": ["eco "],
        "target_subtype": "eco_pla",
        "target_display_name": "eco PLA",
    },
    {
        "manufacturer": "3djake",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "magic_",
        "name_prefix": ["magic "],
        "target_subtype": "magic_pla",
        "target_display_name": "magic PLA",
    },
    {
        "manufacturer": "3djake",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "mystery_",
        "name_prefix": ["mystery "],
        "target_subtype": "mystery_pla",
        "target_display_name": "mystery PLA",
    },
    {
        "manufacturer": "3djake",
        "material": "PLA",
        "source_subtype": "silk_pla",
        "id_prefix": "eco_",
        "name_prefix": ["eco "],
        "target_subtype": "eco_silk_pla",
        "target_display_name": "eco Silk PLA",
    },
    {
        "manufacturer": "3djake",
        "material": "PLA",
        "source_subtype": "matte_pla",
        "id_prefix": "eco_",
        "name_prefix": ["eco "],
        "target_subtype": "eco_matte_pla",
        "target_display_name": "eco Matte PLA",
    },
    {
        "manufacturer": "3djake",
        "material": "PLA",
        "source_subtype": "glow_pla",
        "id_prefix": "eco_",
        "name_prefix": ["eco "],
        "target_subtype": "eco_glow_pla",
        "target_display_name": "eco Glow PLA",
    },

    # =========================================================================
    # Winkle PLA
    # =========================================================================
    {
        "manufacturer": "winkle",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "hd_",
        "name_prefix": ["HD "],
        "target_subtype": "hd_pla",
        "target_display_name": "HD PLA",
    },

    # =========================================================================
    # Tinmorry PETG
    # Note: some names have double spaces (e.g. "Metallic  Blue")
    # =========================================================================
    {
        "manufacturer": "tinmorry",
        "material": "PETG",
        "source_subtype": "petg",
        "id_prefix": "rapid_eco_",
        "name_prefix": ["Rapid -Eco ", "Rapid-Eco ", "Rapid Eco "],
        "target_subtype": "rapid_eco_petg",
        "target_display_name": "Rapid-Eco PETG",
    },
    {
        "manufacturer": "tinmorry",
        "material": "PETG",
        "source_subtype": "petg",
        "id_prefix": "marble_",
        "name_prefix": ["Marble "],
        "target_subtype": "marble_petg",
        "target_display_name": "Marble PETG",
    },
    {
        "manufacturer": "tinmorry",
        "material": "PETG",
        "source_subtype": "petg",
        "id_prefix": "metallic_",
        "name_prefix": ["Metallic  ", "Metallic "],
        "target_subtype": "metallic_petg",
        "target_display_name": "Metallic PETG",
    },
    {
        "manufacturer": "tinmorry",
        "material": "PETG",
        "source_subtype": "petg",
        "id_prefix": "galaxy_",
        "name_prefix": ["Galaxy  ", "Galaxy "],
        "target_subtype": "galaxy_petg",
        "target_display_name": "Galaxy PETG",
    },

    # =========================================================================
    # Amolen silk_pla
    # =========================================================================
    {
        "manufacturer": "amolen",
        "material": "PLA",
        "source_subtype": "silk_pla",
        "id_prefix": "basic_",
        "name_prefix": ["Basic "],
        "target_subtype": "basic_silk_pla",
        "target_display_name": "Basic Silk PLA",
    },
    {
        "manufacturer": "amolen",
        "material": "PLA",
        "source_subtype": "silk_pla",
        "id_prefix": "dual_color_",
        "name_prefix": ["Dual Color "],
        "target_subtype": "dual_color_silk_pla",
        "target_display_name": "Dual Color Silk PLA",
    },
    {
        "manufacturer": "amolen",
        "material": "PLA",
        "source_subtype": "silk_pla",
        "id_prefix": "s_series_",
        "name_prefix": ["S-Series "],
        "target_subtype": "s_series_silk_pla",
        "target_display_name": "S-Series Silk PLA",
    },
    {
        "manufacturer": "amolen",
        "material": "PLA",
        "source_subtype": "silk_pla",
        "id_prefix": "triple_color_",
        "name_prefix": ["Triple Color "],
        "target_subtype": "triple_color_silk_pla",
        "target_display_name": "Triple Color Silk PLA",
    },
    {
        "manufacturer": "amolen",
        "material": "PLA",
        "source_subtype": "silk_pla",
        "id_prefix": "shiny_gradient_",
        "name_prefix": ["Shiny Gradient "],
        "target_subtype": "shiny_gradient_silk_pla",
        "target_display_name": "Shiny Gradient Silk PLA",
    },
    {
        "manufacturer": "amolen",
        "material": "PLA",
        "source_subtype": "silk_pla",
        "id_prefix": "shiny_glitter_",
        "name_prefix": ["Shiny Glitter "],
        "target_subtype": "shiny_glitter_silk_pla",
        "target_display_name": "Shiny Glitter Silk PLA",
    },
    {
        "manufacturer": "amolen",
        "material": "PLA",
        "source_subtype": "silk_pla",
        "id_prefix": "rainbow_",
        "name_prefix": ["Rainbow "],
        "target_subtype": "rainbow_silk_pla",
        "target_display_name": "Rainbow Silk PLA",
    },

    # =========================================================================
    # Amolen pla
    # =========================================================================
    {
        "manufacturer": "amolen",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "crystal_transparent_",
        "name_prefix": ["Crystal-Transparent ", "Crystal Transparent "],
        "target_subtype": "crystal_transparent_pla",
        "target_display_name": "Crystal Transparent PLA",
    },
    {
        "manufacturer": "amolen",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "marble_",
        "name_prefix": ["Marble "],
        "target_subtype": "marble_pla",
        "target_display_name": "Marble PLA",
    },
    {
        "manufacturer": "amolen",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "wood_",
        "name_prefix": ["Wood "],
        "target_subtype": "wood_pla",
        "target_display_name": "Wood PLA",
    },
    {
        "manufacturer": "amolen",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "transparent_",
        "name_prefix": ["Transparent "],
        "target_subtype": "transparent_pla",
        "target_display_name": "Transparent PLA",
    },
    {
        "manufacturer": "amolen",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "temperature_color_change_",
        "name_prefix": ["Temperature Color Change "],
        "target_subtype": "temperature_color_change_pla",
        "target_display_name": "Temperature Color Change PLA",
    },
    {
        "manufacturer": "amolen",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "uv_color_change_",
        "name_prefix": ["UV Color Change "],
        "target_subtype": "uv_color_change_pla",
        "target_display_name": "UV Color Change PLA",
    },

    # =========================================================================
    # Amolen matte_pla
    # =========================================================================
    {
        "manufacturer": "amolen",
        "material": "PLA",
        "source_subtype": "matte_pla",
        "id_prefix": "dual_color_",
        "name_prefix": ["Dual Color "],
        "target_subtype": "dual_color_matte_pla",
        "target_display_name": "Dual Color Matte PLA",
    },
    {
        "manufacturer": "amolen",
        "material": "PLA",
        "source_subtype": "matte_pla",
        "id_prefix": "triple_color_",
        "name_prefix": ["Triple Color ", "Triple "],
        "target_subtype": "triple_color_matte_pla",
        "target_display_name": "Triple Color Matte PLA",
    },
    {
        "manufacturer": "amolen",
        "material": "PLA",
        "source_subtype": "matte_pla",
        "id_prefix": "basic_",
        "name_prefix": ["Basic "],
        "target_subtype": "basic_matte_pla",
        "target_display_name": "Basic Matte PLA",
    },

    # =========================================================================
    # Smart Materials 3D PLA
    # =========================================================================
    {
        "manufacturer": "smart_materials_3d",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "recycled_",
        "name_prefix": ["RECYCLED "],
        "target_subtype": "recycled_pla",
        "target_display_name": "Recycled PLA",
    },
    {
        "manufacturer": "smart_materials_3d",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "wood_",
        "name_prefix": ["WOOD "],
        "target_subtype": "wood_pla",
        "target_display_name": "Wood PLA",
    },
    {
        "manufacturer": "smart_materials_3d",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "pastel_",
        "name_prefix": ["PASTEL "],
        "target_subtype": "pastel_pla",
        "target_display_name": "Pastel PLA",
    },
    {
        "manufacturer": "smart_materials_3d",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "crystal_",
        "name_prefix": ["Crystal "],
        "target_subtype": "crystal_pla",
        "target_display_name": "Crystal PLA",
    },
    {
        "manufacturer": "smart_materials_3d",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "neon_",
        "name_prefix": ["NEON "],
        "target_subtype": "neon_pla",
        "target_display_name": "Neon PLA",
    },

    # =========================================================================
    # Spectrum PLA - pla/ still has many product-line prefixed variants
    # Some target directories already exist (will skip filament.json creation)
    # =========================================================================
    {
        "manufacturer": "spectrum",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "premium_",
        "name_prefix": ["Premium  ", "Premium "],
        "target_subtype": "pla_premium",
        "target_display_name": "PLA Premium",
    },
    {
        "manufacturer": "spectrum",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "the_filament_",
        "name_prefix": ["The Filament  ", "The Filament "],
        "target_subtype": "the_filament_pla",
        "target_display_name": "The Filament PLA",
    },
    {
        "manufacturer": "spectrum",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "pastello_",
        "name_prefix": ["Pastello  ", "Pastello "],
        "target_subtype": "pastello_pla",
        "target_display_name": "Pastello PLA",
    },
    {
        "manufacturer": "spectrum",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "safeguard_",
        "name_prefix": ["Safeguard  ", "Safeguard "],
        "target_subtype": "safeguard_pla",
        "target_display_name": "Safeguard PLA",
    },
    {
        "manufacturer": "spectrum",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "r_",
        "name_prefix": ["r "],
        "target_subtype": "r_pla",
        "target_display_name": "R PLA",
    },
    {
        "manufacturer": "spectrum",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "lw_ultrafoam_",
        "name_prefix": ["LW-UltraFoam ", "LW UltraFoam ", "lw_ultrafoam "],
        "target_subtype": "lw_pla_ultrafoam",
        "target_display_name": "LW PLA UltraFoam",
    },
    {
        "manufacturer": "spectrum",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "nature_",
        "name_prefix": ["Nature  ", "Nature "],
        "target_subtype": "pla_nature",
        "target_display_name": "PLA Nature",
    },
    {
        "manufacturer": "spectrum",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "stone_age_",
        "name_prefix": ["Stone Age\u2122 ", "Stone Age  ", "Stone Age "],
        "target_subtype": "stone_age_pla",
        "target_display_name": "Stone Age PLA",
    },
    {
        "manufacturer": "spectrum",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "greenyht_",
        "name_prefix": ["GreenyHT ", "greenyht "],
        "target_subtype": "greenyht",
        "target_display_name": "GreenyHT",
    },

    # =========================================================================
    # Sunlu PLA - pla/ has many product-line prefixed variants
    # Some targets already exist (pla+, pla_classic, pla_meta, pla_rainbow)
    # =========================================================================
    {
        "manufacturer": "sunlu",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "upgrade_",
        "name_prefix": ["Upgrade + ", "Upgrade "],
        "target_subtype": "upgrade_pla",
        "target_display_name": "Upgrade PLA",
    },
    {
        "manufacturer": "sunlu",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "plus_",
        "name_prefix": ["PLA+ ", "Plus ", "PLA Plus "],
        "target_subtype": "pla+",
        "target_display_name": "PLA+",
    },
    {
        "manufacturer": "sunlu",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "rainbow_",
        "name_prefix": ["Rainbow "],
        "target_subtype": "pla_rainbow",
        "target_display_name": "PLA Rainbow",
    },
    {
        "manufacturer": "sunlu",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "twinkling_",
        "name_prefix": ["Twinkling "],
        "target_subtype": "pla_twinkling",
        "target_display_name": "PLA Twinkling",
    },
    {
        "manufacturer": "sunlu",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "real_wood_fiber_",
        "name_prefix": ["Real Wood Fiber ", "Real-Wood-Fiber "],
        "target_subtype": "real_wood_fiber_pla",
        "target_display_name": "Real Wood Fiber PLA",
    },
    {
        "manufacturer": "sunlu",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "meta_",
        "name_prefix": ["Meta "],
        "target_subtype": "pla_meta",
        "target_display_name": "PLA Meta",
    },
    {
        "manufacturer": "sunlu",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "transparentclear_",
        "name_prefix": ["Transparent(Clear) ", "TransparentClear "],
        "target_subtype": "transparent_clear_pla",
        "target_display_name": "Transparent Clear PLA",
    },
    {
        "manufacturer": "sunlu",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "temperature_color_change_",
        "name_prefix": ["Temperature Color Change "],
        "target_subtype": "temperature_color_change_pla",
        "target_display_name": "Temperature Color Change PLA",
    },
    {
        "manufacturer": "sunlu",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "fluorescent_",
        "name_prefix": ["Fluorescent "],
        "target_subtype": "fluorescent_pla",
        "target_display_name": "Fluorescent PLA",
    },
]


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def strip_name_prefix(name: str, name_prefixes: list[str]) -> str:
    """Strip the product-line prefix from the display name.

    Tries each prefix in order (longest first for safety).
    """
    # Sort by length descending to match longest prefix first
    for prefix in sorted(name_prefixes, key=len, reverse=True):
        if name.startswith(prefix):
            stripped = name[len(prefix):].strip()
            if stripped:
                return stripped[0].upper() + stripped[1:]
            return name

    # Try case-insensitive match
    for prefix in sorted(name_prefixes, key=len, reverse=True):
        if name.lower().startswith(prefix.lower()):
            stripped = name[len(prefix):].strip()
            if stripped:
                return stripped[0].upper() + stripped[1:]
            return name

    print(f"  WARNING: Name '{name}' doesn't match any prefix {name_prefixes}, keeping as-is")
    return name


def create_filament_json(source_path: Path, target_path: Path, target_id: str, target_name: str):
    """Create a filament.json for the new subtype by copying from source."""
    source_filament = source_path / "filament.json"
    target_filament = target_path / "filament.json"

    if target_filament.exists():
        return False  # Already created

    if source_filament.exists():
        data = load_json(source_filament)
        data["id"] = target_id
        data["name"] = target_name
        save_json(target_filament, data)
    else:
        save_json(target_filament, {
            "id": target_id,
            "name": target_name,
            "diameter_tolerance": 0.02,
            "density": 1.24,
            "min_print_temperature": 190,
            "max_print_temperature": 230,
            "min_bed_temperature": 50,
            "max_bed_temperature": 70,
        })
    return True


def process_rule(rule: dict, dry_run: bool = False, delete_dupes: bool = False) -> dict:
    """Process a single move rule. Returns stats dict."""
    stats = {"moved": 0, "skipped": 0, "conflicts": 0, "deleted_dupes": 0, "created": False}
    mfg = rule["manufacturer"]
    material = rule["material"]
    source_sub = rule["source_subtype"]
    id_prefix = rule["id_prefix"]
    name_prefixes = rule["name_prefix"]
    target_sub = rule["target_subtype"]
    target_name = rule["target_display_name"]

    source_path = DATA_DIR / mfg / material / source_sub
    target_path = DATA_DIR / mfg / material / target_sub

    if not source_path.exists():
        print(f"  SKIP: Source {mfg}/{material}/{source_sub} does not exist")
        return stats

    # Find matching variant directories
    matching = []
    for entry in sorted(source_path.iterdir()):
        if entry.is_dir() and entry.name.startswith(id_prefix):
            matching.append(entry)

    if not matching:
        print(f"  SKIP: No variants matching '{id_prefix}*' in {mfg}/{material}/{source_sub}")
        return stats

    print(f"  Found {len(matching)} variants with prefix '{id_prefix}'")

    # Create target directory and filament.json
    if not dry_run:
        target_path.mkdir(parents=True, exist_ok=True)
        created = create_filament_json(source_path, target_path, target_sub, target_name)
        if created:
            stats["created"] = True
            print(f"  CREATED: {mfg}/{material}/{target_sub}/filament.json")
    else:
        if not (target_path / "filament.json").exists():
            stats["created"] = True
            print(f"  WOULD CREATE: {mfg}/{material}/{target_sub}/filament.json")

    # Move each matching variant
    for variant_dir in matching:
        old_id = variant_dir.name
        new_id = old_id[len(id_prefix):]

        if not new_id:
            print(f"  SKIP: Stripping '{id_prefix}' from '{old_id}' leaves empty id")
            stats["skipped"] += 1
            continue

        new_variant_path = target_path / new_id

        # Check for conflict (target already exists)
        if new_variant_path.exists():
            if delete_dupes:
                if not dry_run:
                    shutil.rmtree(str(variant_dir))
                print(f"  DUPE-DEL: {old_id} (target {target_sub}/{new_id} exists)")
                stats["deleted_dupes"] += 1
            else:
                print(f"  CONFLICT: {target_sub}/{new_id} already exists, skipping {old_id}")
                stats["conflicts"] += 1
            continue

        # Read and update variant.json
        variant_json_path = variant_dir / "variant.json"
        if variant_json_path.exists():
            variant_data = load_json(variant_json_path)
            old_name = variant_data.get("name", "")
            new_name = strip_name_prefix(old_name, name_prefixes)

            variant_data["id"] = new_id
            variant_data["name"] = new_name

            if not dry_run:
                save_json(variant_json_path, variant_data)
        else:
            print(f"  WARNING: No variant.json in {old_id}")

        # Move the directory
        if not dry_run:
            shutil.move(str(variant_dir), str(new_variant_path))

        print(f"  MOVE: {old_id} → {target_sub}/{new_id}")
        stats["moved"] += 1

    return stats


def cleanup_empty_dirs(dry_run: bool = False) -> int:
    """Report subtype directories with no variant subdirectories."""
    count = 0
    for mfg_dir in sorted(DATA_DIR.iterdir()):
        if not mfg_dir.is_dir() or mfg_dir.name.startswith("."):
            continue
        for material_dir in sorted(mfg_dir.iterdir()):
            if not material_dir.is_dir():
                continue
            for subtype_dir in sorted(material_dir.iterdir()):
                if not subtype_dir.is_dir():
                    continue
                has_variants = any(p.is_dir() for p in subtype_dir.iterdir())
                if not has_variants:
                    remaining = list(subtype_dir.iterdir())
                    if len(remaining) <= 1:
                        rel = subtype_dir.relative_to(DATA_DIR)
                        print(f"  EMPTY: {rel}")
                        count += 1
    return count


def main():
    dry_run = "--dry-run" in sys.argv
    delete_dupes = "--delete-dupes" in sys.argv

    if dry_run:
        print("=== DRY RUN MODE - No changes will be made ===\n")

    total_moved = 0
    total_created = 0
    total_conflicts = 0
    total_deleted = 0
    current_mfg = None

    for rule in MOVE_RULES:
        mfg = rule["manufacturer"]
        if mfg != current_mfg:
            current_mfg = mfg
            print(f"\n{'='*60}")
            print(f" {mfg}")
            print(f"{'='*60}")

        header = f"{rule['source_subtype']} [{rule['id_prefix']}*] → {rule['target_subtype']}"
        print(f"\n{header}")

        stats = process_rule(rule, dry_run=dry_run, delete_dupes=delete_dupes)
        total_moved += stats["moved"]
        total_conflicts += stats["conflicts"]
        total_deleted += stats["deleted_dupes"]
        if stats["created"]:
            total_created += 1

    print(f"\n{'='*60}")
    print(f" Checking for empty directories")
    print(f"{'='*60}")
    empty_count = cleanup_empty_dirs(dry_run=dry_run)

    print(f"\n{'='*60}")
    print(f" SUMMARY")
    print(f"{'='*60}")
    print(f"  New subtypes created:  {total_created}")
    print(f"  Variants moved:        {total_moved}")
    print(f"  Conflicts (skipped):   {total_conflicts}")
    print(f"  Duplicates deleted:    {total_deleted}")
    print(f"  Empty dirs found:      {empty_count}")

    if dry_run:
        print("\nRun without --dry-run to apply changes.")
    if total_conflicts > 0 and not delete_dupes:
        print("Run with --delete-dupes to remove source variants when target already exists.")


if __name__ == "__main__":
    main()

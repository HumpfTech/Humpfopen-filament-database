#!/usr/bin/env python3
"""One-time script to fix the 70 remaining manual review items from the OPT cleanup report.

Handles:
  - Redundant suffix stripping (heat_activated, uv_reactive, black_light_reactive)
  - Redundant prefix stripping (flexible_, glass_fiber_reinforced_, temperature_color_change_)
  - Product line splits (tectonic_3d, protopasta, coex_3d, push_plastic)
  - Description trimming (filacube, francofil, eryone, protopasta)
  - Trait additions where properties are moved from name to traits
  - Broken word boundary fixes (primacreator, amolen)
  - Numeric variant ID context additions (das_filament, prusament)

Usage:
  python fix_manual_review.py              # dry-run, prints what would be done
  python fix_manual_review.py --apply      # apply fixes
"""

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

UPPERCASE_WORDS = {
    "ht", "fme", "pmuc", "ral", "pei", "pla", "petg", "abs", "asa",
    "tpu", "tpe", "pekk", "ppe", "ppsu", "tpi", "cf", "mc", "sc",
    "uv", "fst1", "3d4000fl", "pa11", "pa6", "gf", "cc",
}

LOWERCASE_WORDS = {"to", "of", "in", "the", "a", "and", "or"}


def load_json(path: Path) -> Optional[dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def make_display_name(slug: str) -> str:
    """Convert slug to display name with proper capitalization."""
    words = slug.replace("_", " ").split()
    result = []
    for i, word in enumerate(words):
        lower = word.lower()
        if lower in UPPERCASE_WORDS:
            result.append(word.upper())
        elif i > 0 and lower in LOWERCASE_WORDS:
            result.append(lower)
        else:
            result.append(word.title())
    return " ".join(result)


# ---------------------------------------------------------------------------
# Rename mappings: old_path (relative to data/) -> new_variant_id
# ---------------------------------------------------------------------------

RENAMES: dict[str, str] = {
    # --- Strip _heat_activated suffix (gizmo_dorks) ---
    "gizmo_dorks/ABS/abs/color_change_blue_to_white_heat_activated":
        "color_change_blue_to_white",
    "gizmo_dorks/ABS/abs/color_change_green_to_yellow_heat_activated":
        "color_change_green_to_yellow",
    "gizmo_dorks/ABS/abs/color_change_grey_to_white_heat_activated":
        "color_change_grey_to_white",
    "gizmo_dorks/ABS/abs/color_change_purple_to_pink_heat_activated":
        "color_change_purple_to_pink",
    "gizmo_dorks/PLA/pla/color_change_blue_to_white_heat_activated":
        "color_change_blue_to_white",
    "gizmo_dorks/PLA/pla/color_change_green_to_yellow_heat_activated":
        "color_change_green_to_yellow",
    "gizmo_dorks/PLA/pla/color_change_grey_to_white_heat_activated":
        "color_change_grey_to_white",
    "gizmo_dorks/PLA/pla/color_change_purple_to_pink_heat_activated":
        "color_change_purple_to_pink",

    # --- Strip _black_light_reactive (gizmo_dorks, UV reactive) ---
    "gizmo_dorks/ABS/abs/fluorescent_hot_pink_black_light_reactive":
        "fluorescent_hot_pink",

    # --- Strip _uv_reactive suffix + extra marketing words (atomic_filament) ---
    "atomic_filament/PETG/petg/extreme_translucent_fluorescent_neon_green_uv_reactive":
        "translucent_fluorescent_neon_green",
    "atomic_filament/PETG/petg/pearlescent_translucent_neon_green_v2_uv_reactive":
        "pearlescent_translucent_neon_green_v2",
    "atomic_filament/PLA/pla/fluorescent_translucent_neon_hot_pink_uv_reactive":
        "fluorescent_translucent_neon_hot_pink",
    "atomic_filament/PLA/pla/pearlescent_translucent_neon_green_v2_uv_reactive":
        "pearlescent_translucent_neon_green_v2",
    "atomic_filament/PLA/pla/pearlescent_translucent_neon_yellow_uv_reactive":
        "pearlescent_translucent_neon_yellow",
    "atomic_filament/PLA/silk_pla/silky_extreme_bright_neon_green_uv_reactive":
        "silky_extreme_bright_neon_green",
    "atomic_filament/PLA/silk_pla/silky_extreme_bright_neon_pink_uv_reactive":
        "silky_extreme_bright_neon_pink",

    # --- Strip temperature_color_change_ prefix (amolen PLA — captured in traits) ---
    "amolen/PLA/pla/temperature_color_change_black_red_yellow":
        "black_red_yellow",
    "amolen/PLA/pla/temperature_color_change_black_to_red_to_yellow":
        "black_to_red_to_yellow",
    "amolen/PLA/pla/temperature_color_change_purple_green_to_pink_yellow":
        "purple_green_to_pink_yellow",

    # --- Strip glass_fiber_reinforced_ prefix (tinmorry — redundant with gf_petg) ---
    "tinmorry/PETG/gf_petg/glass_fiber_reinforced_frosted_carter_yellow":
        "frosted_carter_yellow",

    # --- Francofil: shorten expanded FME acronym ---
    "francofil/ABS/abs/rose_fme_foreign_material_exclusion_pmuc_certified":
        "rose_fme_pmuc",
    "francofil/ASA/asa/rose_fme_foreign_material_exclusion_pmuc_certified":
        "rose_fme_pmuc",
    "francofil/PETG/petg/rose_fme_foreign_material_exclusion_pmuc_certified":
        "rose_fme_pmuc",

    # --- Filacube: strip verbose marketing descriptions, keep color + generation ---
    "filacube/PLA/pla/iced_coffee_light_brown_tan_beige_caramel_latte_2":
        "iced_coffee_2",
    "filacube/PLA/pla/ivory_white_off_whitecreamy_whiteslightly_yellowish_white_2":
        "ivory_white_2",
    "filacube/PLA/pla/maroon_reddish_purple_or_dark_brownish_red_2":
        "maroon_2",
    "filacube/PLA/pla/ultra_violet_blue_based_purple_carrying_a_vibe_of_innovationluxurymystique_2":
        "ultra_violet_2",

    # --- Eryone quad-color: strip color descriptions, keep creative name ---
    "eryone/PLA/pla_silk_high_speed_quadruple/aurora_dream_tea_green_violet_electric_pink_indigo":
        "aurora_dream",
    "eryone/PLA/pla_silk_high_speed_quadruple/cold_flame_night_attack_dark_purple_magenta_pink_sky_blue":
        "cold_flame_night_attack",
    "eryone/PLA/pla_silk_high_speed_quadruple/electric_night_neon_purple_bright_blue_neon_pink_neon_yellow":
        "electric_night",
    "eryone/PLA/pla_silk_high_speed_quadruple/emerald_athens_silver_rose_gold_emerald_green_wine_red":
        "emerald_athens",
    "eryone/PLA/pla_silk_high_speed_quadruple/metallic_frenzy_black_dark_red_banana_orange_gold":
        "metallic_frenzy",
    "eryone/PLA/pla_silk_high_speed_quadruple/pond_of_the_underworld_red_purple_blue_green":
        "pond_of_the_underworld",
    "eryone/PLA/pla_silk_high_speed_quadruple/royal_essence_black_purple_silver_dark_green":
        "royal_essence",
    "eryone/PLA/pla_burnt_titanium_rainbow/fantasy_glaze_rose_red_dark_gold_green_blue_purple_blue":
        "fantasy_glaze",

    # --- Flashforge: strip gradient_ prefix ---
    "flashforge/PLA/chameleon_pla/gradient_rapid_burnt_titanium_abyssal_rede":
        "rapid_burnt_titanium_abyssal_rede",
    "flashforge/PLA/chameleon_pla/gradient_rapid_burnt_titanium_nebula_purple":
        "rapid_burnt_titanium_nebula_purple",

    # --- cc3d: strip heat_temp_color_changing_ prefix (captured in trait) ---
    "cc3d/PLA/pla/heat_temp_color_changing_purple_blue_to_pink":
        "purple_blue_to_pink",

    # --- Protopasta: strip verbose descriptors, keep creative name + HT ---
    "protopasta/PETG/petg/amies_blood_of_my_enemies_translucent_red":
        "amies_blood_of_my_enemies",
    "protopasta/PLA/glow_pla/nebula_night_glow_fluorescent_multicolor_ht":
        "nebula_night_ht",
    "protopasta/PLA/pla/amies_blood_of_my_enemies_translucent_red_ht":
        "amies_blood_of_my_enemies_ht",
    "protopasta/PLA/pla/empire_strikes_black_ht_with_silver_glitter":
        "empire_strikes_black_ht",
    "protopasta/PLA/pla/gold_dust_translucent_ht_with_gold_glitter":
        "gold_dust_ht",
    "protopasta/PLA/silk_pla/artobot_electric_lemonade_metallic_yellow_ht":
        "artobot_electric_lemonade_ht",

    # --- Rosa3d: strip color descriptions after creative name ---
    "rosa3d_filaments/PLA/pla/magic_neon_blue_lagoon_neon_green_blue_sky":
        "magic_neon_blue_lagoon",
    "rosa3d_filaments/PLA/pla/magic_neon_mojito_neon_yellow_juicy_green":
        "magic_neon_mojito",

    # --- Ataraxia art: remove redundant trailing _rainbow ---
    "ataraxia_art/PLA/silk_pla/rainbow_shiny_fast_multicolor_change_rainbow":
        "rainbow_shiny_fast_multicolor",

    # --- Category 4: Numeric variant IDs — add context ---
    "das_filament/PETG/petg/7016":
        "ral_7016",
    "prusament/PETG/petg_tungsten/75":
        "75_percent",

    # --- Broken word boundaries (primacreator) ---
    "primacreator/PLA/primaselect_pla/gradient_golddeep_greendeep_blueblue_purplecopperred":
        "gradient_gold_green_blue_purple_copper_red",
    "primacreator/PLA/primaselect_pla/gradient_yellowgreensky_bluepurplerose_redkashmir_gold":
        "gradient_yellow_green_blue_purple_red_gold",

    # --- Broken word boundaries (amolen) ---
    "amolen/PLA/silk_pla/triple_color_purpleblue_greenburnt_orange":
        "triple_color_purple_blue_green_orange",
}

# ---------------------------------------------------------------------------
# Display name overrides for cases where make_display_name() isn't enough
# ---------------------------------------------------------------------------

NAME_OVERRIDES: dict[str, str] = {
    "amies_blood_of_my_enemies": "Amie's Blood of My Enemies",
    "amies_blood_of_my_enemies_ht": "Amie's Blood of My Enemies HT",
    "75_percent": "75%",
    "pond_of_the_underworld": "Pond of the Underworld",
    "cold_flame_night_attack": "Cold Flame Night Attack",
    "gold_dust_ht": "Gold Dust HT",
    "nebula_night_ht": "Nebula Night HT",
    "empire_strikes_black_ht": "Empire Strikes Black HT",
    "artobot_electric_lemonade_ht": "Artobot Electric Lemonade HT",
    "rose_fme_pmuc": "Rose FME PMUC",
}

# ---------------------------------------------------------------------------
# Traits to ensure on renamed variants (keyed by NEW path relative to data/)
# ---------------------------------------------------------------------------

TRAIT_ADDITIONS: dict[str, dict[str, bool]] = {
    # heat_activated stripped -> ensure temperature_color_change trait
    "gizmo_dorks/ABS/abs/color_change_blue_to_white": {"temperature_color_change": True},
    "gizmo_dorks/ABS/abs/color_change_green_to_yellow": {"temperature_color_change": True},
    "gizmo_dorks/ABS/abs/color_change_grey_to_white": {"temperature_color_change": True},
    "gizmo_dorks/ABS/abs/color_change_purple_to_pink": {"temperature_color_change": True},
    "gizmo_dorks/PLA/pla/color_change_blue_to_white": {"temperature_color_change": True},
    "gizmo_dorks/PLA/pla/color_change_green_to_yellow": {"temperature_color_change": True},
    "gizmo_dorks/PLA/pla/color_change_grey_to_white": {"temperature_color_change": True},
    "gizmo_dorks/PLA/pla/color_change_purple_to_pink": {"temperature_color_change": True},

    # black_light_reactive stripped -> add uv_reactive trait
    "gizmo_dorks/ABS/abs/fluorescent_hot_pink": {"uv_reactive": True},

    # uv_reactive stripped from name -> ensure trait
    "atomic_filament/PETG/petg/translucent_fluorescent_neon_green": {"uv_reactive": True},
    "atomic_filament/PETG/petg/pearlescent_translucent_neon_green_v2": {"uv_reactive": True},
    "atomic_filament/PLA/pla/fluorescent_translucent_neon_hot_pink": {"uv_reactive": True},
    "atomic_filament/PLA/pla/pearlescent_translucent_neon_green_v2": {"uv_reactive": True},
    "atomic_filament/PLA/pla/pearlescent_translucent_neon_yellow": {"uv_reactive": True},
    "atomic_filament/PLA/silk_pla/silky_extreme_bright_neon_green": {"uv_reactive": True},
    "atomic_filament/PLA/silk_pla/silky_extreme_bright_neon_pink": {"uv_reactive": True},

    # temperature_color_change prefix stripped -> ensure trait
    "amolen/PLA/pla/black_red_yellow": {"temperature_color_change": True},
    "amolen/PLA/pla/black_to_red_to_yellow": {"temperature_color_change": True},
    "amolen/PLA/pla/purple_green_to_pink_yellow": {"temperature_color_change": True},

    # cc3d heat_temp_color_changing stripped -> ensure trait
    "cc3d/PLA/pla/purple_blue_to_pink": {"temperature_color_change": True},
}

# ---------------------------------------------------------------------------
# Product line splits: old_path -> (new_filament_id, new_variant_id)
# ---------------------------------------------------------------------------

PRODUCT_LINE_SPLITS: dict[str, tuple[str, str]] = {
    # coex_3d Hytrel product line
    "coex_3d/TPU/tpu/hytrel_3d4000fl_bk513_40d":
        ("hytrel_3d4000fl_tpu", "bk513_40d"),
    "coex_3d/TPU/tpu/hytrel_3d4000fl_nc010_40d":
        ("hytrel_3d4000fl_tpu", "nc010_40d"),

    # protopasta stainless steel metal composite
    "protopasta/PLA/pla/stainless_steel_metal_composite_blue_color":
        ("stainless_steel_metal_composite_pla", "blue"),
    "protopasta/PLA/pla/stainless_steel_metal_composite_burgundy_color":
        ("stainless_steel_metal_composite_pla", "burgundy"),
    "protopasta/PLA/pla/stainless_steel_metal_composite_gold_color":
        ("stainless_steel_metal_composite_pla", "gold"),

    # push_plastic PEI grade -> product line
    "push_plastic/PEI/pei/1010":
        ("pei_1010", "natural"),

    # tectonic_3d product lines
    "tectonic_3d/PA11/cf_pa11/zephyr_cf_mc_extreme_light_weight_thermal_resistance":
        ("zephyr_cf_mc_cf_pa11", "black"),
    "tectonic_3d/PEI/pei/vulcan_1010_natural_flame_retardant_low_smoke":
        ("vulcan_1010_pei", "natural"),
    "tectonic_3d/PEI/pei/vulcan_9085_natural_flame_retardant_low_smoke":
        ("vulcan_9085_pei", "natural"),
    "tectonic_3d/PEKK/pekk/vulcan_a_natural_flame_retardant_chemical_resistance":
        ("vulcan_a_pekk", "natural"),
    "tectonic_3d/PEKK/pekk/vulcan_sc_flame_retardant_superior_thermal_resistance":
        ("vulcan_sc_pekk", "natural"),
    "tectonic_3d/PPE/ppe/atar_fst1_flame_retardant_low_smoke_black":
        ("atar_fst1_ppe", "black"),
    "tectonic_3d/PPSU/ppsu/vulcan_natural_excellent_in_humidity_environments":
        ("vulcan_ppsu", "natural"),
    "tectonic_3d/TPI/tpi/vulcan_pi_natural_flame_retardant_highest_z_strength":
        ("vulcan_pi_tpi", "natural"),
}

# Display name overrides for split variant IDs
SPLIT_VARIANT_NAME_OVERRIDES: dict[str, str] = {
    "bk513_40d": "BK513 40D",
    "nc010_40d": "NC010 40D",
}

# Display name overrides for new filament directory IDs
FILAMENT_NAME_OVERRIDES: dict[str, str] = {
    "hytrel_3d4000fl_tpu": "Hytrel 3D4000FL TPU",
    "pei_1010": "PEI 1010",
    "stainless_steel_metal_composite_pla": "Stainless Steel Metal Composite PLA",
    "zephyr_cf_mc_cf_pa11": "Zephyr CF MC CF PA11",
    "vulcan_1010_pei": "Vulcan 1010 PEI",
    "vulcan_9085_pei": "Vulcan 9085 PEI",
    "vulcan_a_pekk": "Vulcan A PEKK",
    "vulcan_sc_pekk": "Vulcan SC PEKK",
    "atar_fst1_ppe": "Atar FST1 PPE",
    "vulcan_ppsu": "Vulcan PPSU",
    "vulcan_pi_tpi": "Vulcan Pi TPI",
}

# Exact duplicates to delete (non-prefixed version already exists with identical data)
DUPLICATES_TO_DELETE = [
    "amolen/TPU/tpu/flexible_blue_green_orange_translucent_rainbow",
    "amolen/TPU/tpu/flexible_pink_blue_green_orange_transparent_rainbow",
    "amolen/TPU/tpu/flexible_red_green_purple_orange_translucent_rainbow",
    "amolen/TPU/tpu/flexible_yellow_green_orange_translucent_rainbow",
]

# Items explicitly left as-is (multi-color names that are naturally long)
SKIPPED = [
    "amolen/TPU/tpu/pink_blue_green_orange_transparent_rainbow",
    "amolen/TPU/tpu/purple_pink_orange_green_transparent_rainbow",
    "amolen/TPU/tpu/red_green_purple_orange_translucent_rainbow",
    "epax/PLA/silk_pla/magic_tarnished_copper_gunmetal_gray_copper",
    "sunlu/PLA/silk_pla/rainbow_pale_green_orange_light_pink_yellow",
]


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------

def do_rename(data_dir: Path, old_rel: str, new_variant_id: str,
              dry_run: bool) -> bool:
    """Rename a variant directory and update its variant.json."""
    old_path = data_dir / old_rel
    if not old_path.is_dir():
        print(f"  NOT FOUND: {old_rel}")
        return False

    new_path = old_path.parent / new_variant_id
    if new_path.exists() and new_path != old_path:
        print(f"  COLLISION: {old_rel} -> {new_variant_id} (target exists)")
        return False

    new_name = NAME_OVERRIDES.get(
        new_variant_id, make_display_name(new_variant_id))

    # Build new relative path for trait lookup
    parts = old_rel.split("/")
    new_rel = "/".join(parts[:3]) + "/" + new_variant_id

    print(f"  RENAME: {old_rel}")
    print(f"      -> .../{new_variant_id}  ({new_name})")

    if dry_run:
        return True

    # Move directory
    shutil.move(str(old_path), str(new_path))

    # Update variant.json
    variant_json = new_path / "variant.json"
    if variant_json.exists():
        data = load_json(variant_json)
        if data:
            data["id"] = new_variant_id
            data["name"] = new_name

            # Add/ensure traits
            if new_rel in TRAIT_ADDITIONS:
                traits = data.setdefault("traits", {})
                traits.update(TRAIT_ADDITIONS[new_rel])

            save_json(variant_json, data)

    return True


def do_delete_duplicate(data_dir: Path, old_rel: str, dry_run: bool) -> bool:
    """Delete a duplicate variant directory."""
    old_path = data_dir / old_rel
    if not old_path.is_dir():
        print(f"  NOT FOUND: {old_rel}")
        return False

    print(f"  DELETE: {old_rel}  (duplicate)")

    if dry_run:
        return True

    shutil.rmtree(str(old_path))
    return True


def do_product_line_split(data_dir: Path, old_rel: str,
                          new_filament_id: str, new_variant_id: str,
                          dry_run: bool) -> bool:
    """Move a variant into a new product-line filament directory."""
    old_path = data_dir / old_rel
    if not old_path.is_dir():
        print(f"  NOT FOUND: {old_rel}")
        return False

    parts = old_rel.split("/")
    brand, material, old_filament = parts[0], parts[1], parts[2]
    material_dir = data_dir / brand / material
    new_filament_dir = material_dir / new_filament_id
    new_variant_dir = new_filament_dir / new_variant_id

    if new_variant_dir.exists():
        print(f"  COLLISION: {old_rel} -> {new_filament_id}/{new_variant_id}")
        return False

    variant_name = SPLIT_VARIANT_NAME_OVERRIDES.get(
        new_variant_id, make_display_name(new_variant_id))
    filament_name = FILAMENT_NAME_OVERRIDES.get(
        new_filament_id, make_display_name(new_filament_id))

    print(f"  SPLIT:  {old_rel}")
    print(f"      -> {brand}/{material}/{new_filament_id}/{new_variant_id}"
          f"  ({filament_name} / {variant_name})")

    if dry_run:
        return True

    # Create new filament directory
    new_filament_dir.mkdir(parents=True, exist_ok=True)

    # Create filament.json if it doesn't exist yet
    new_filament_json = new_filament_dir / "filament.json"
    if not new_filament_json.exists():
        # Copy settings from source filament dir
        source_fj = material_dir / old_filament / "filament.json"
        filament_data: dict[str, Any] = {}
        if source_fj.exists():
            loaded = load_json(source_fj)
            if loaded:
                filament_data = loaded.copy()
        filament_data["id"] = new_filament_id
        filament_data["name"] = filament_name
        save_json(new_filament_json, filament_data)

    # Move variant directory
    shutil.move(str(old_path), str(new_variant_dir))

    # Update variant.json
    variant_json = new_variant_dir / "variant.json"
    if variant_json.exists():
        data = load_json(variant_json)
        if data:
            data["id"] = new_variant_id
            data["name"] = variant_name
            save_json(variant_json, data)

    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fix remaining manual review items from OPT cleanup report")
    parser.add_argument(
        "--apply", action="store_true",
        help="Apply fixes (default is dry-run)")
    args = parser.parse_args()

    dry_run = not args.apply
    data_dir = Path(__file__).parent / "data"

    if not data_dir.is_dir():
        print(f"ERROR: data directory not found at {data_dir}")
        return 1

    mode = "DRY RUN" if dry_run else "APPLYING"
    print(f"{'=' * 60}")
    print(f"FIX MANUAL REVIEW ITEMS — {mode}")
    print(f"{'=' * 60}\n")

    ok = 0
    fail = 0

    # --- Process renames ---
    print(f"RENAMES ({len(RENAMES)}):")
    print("-" * 40)
    for old_rel, new_id in RENAMES.items():
        if do_rename(data_dir, old_rel, new_id, dry_run):
            ok += 1
        else:
            fail += 1

    # --- Process duplicate deletions ---
    print(f"\nDUPLICATE DELETIONS ({len(DUPLICATES_TO_DELETE)}):")
    print("-" * 40)
    for old_rel in DUPLICATES_TO_DELETE:
        if do_delete_duplicate(data_dir, old_rel, dry_run):
            ok += 1
        else:
            fail += 1

    # --- Process product line splits ---
    print(f"\nPRODUCT LINE SPLITS ({len(PRODUCT_LINE_SPLITS)}):")
    print("-" * 40)
    for old_rel, (fil_id, var_id) in PRODUCT_LINE_SPLITS.items():
        if do_product_line_split(data_dir, old_rel, fil_id, var_id, dry_run):
            ok += 1
        else:
            fail += 1

    # --- Report skipped ---
    print(f"\nSKIPPED — accepted as-is ({len(SKIPPED)}):")
    print("-" * 40)
    for s in SKIPPED:
        print(f"  {s}")

    # --- Summary ---
    print(f"\n{'=' * 60}")
    print(f"Mode:      {mode}")
    print(f"Success:   {ok}")
    print(f"Failed:    {fail}")
    print(f"Skipped:   {len(SKIPPED)}")
    print(f"Total:     {ok + fail + len(SKIPPED)} / 75")
    print(f"{'=' * 60}")

    if dry_run and fail == 0:
        print("\nRe-run with --apply to execute these changes.")

    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

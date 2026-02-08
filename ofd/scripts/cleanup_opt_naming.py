"""
Cleanup OPT Naming Script - Fix naming issues from the OpenPrintTag import.

Detects and fixes several categories of naming problems in the data/ hierarchy:
  Category 1: Swapped filament/variant layers (colors at filament level)
  Category 2: Series/suffix prefix pollution in variant names
  Category 3: Import prefix pollution in variant names
  Category 4: Technical specs as variant names (report only for leftovers)
  Category 5: Colors merged into filament names (auto-fix via color split)
  Category 6: Overly long variant names (report only for leftovers)
  Category 7: Product line prefix/suffix at variant level (auto-fix)
  Category 8: Universal common-prefix detection (auto-fix)
  Category 9: Broken display names (auto-fix)

Usage:
  ofd script cleanup_opt_naming              # dry-run, prints report
  ofd script cleanup_opt_naming --apply      # apply fixes
  ofd script cleanup_opt_naming --brand X    # limit to one brand
  ofd script cleanup_opt_naming --category N # only one category
"""

import argparse
import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from ofd.base import BaseScript, ScriptResult, register_script


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KNOWN_COLORS = {
    "black", "white", "red", "blue", "green", "yellow", "orange",
    "purple", "pink", "grey", "gray", "clear", "natural", "gold",
    "silver", "bronze", "copper", "brown", "cyan", "magenta",
    "violet", "teal", "beige", "ivory", "charcoal", "cream",
    "maroon", "navy", "olive", "coral", "salmon", "lime",
    "turquoise", "indigo", "scarlet", "amber",
}

COLOR_MODIFIERS = {
    "neon", "dark", "light", "bright", "galaxy", "matte", "pastel",
    "deep", "pale", "hot", "liquid", "kaoss", "mango", "midnight",
    "cherry", "luminous", "mojito",
}

MATERIAL_KEYWORDS = {
    "tpu", "pla", "petg", "abs", "asa", "pa", "pc", "pva", "hips",
    "pctg", "pvdf", "pom", "peek", "pei", "flexible", "speed",
}

# Brand-specific prefix rules for Categories 2 and 3.
# Each entry: prefix -> {"action": "strip"|"flag", "name_pattern": regex to clean display name}
PREFIX_RULES: dict[str, dict[str, dict[str, str]]] = {
    "matter3d_inc": {
        "basics_series_": {
            "action": "strip",
            "name_pattern": r"^Basics\s+Series\s*[-–—]?\s*",
        },
        "hf_": {
            "action": "strip",
            "name_pattern": r"^HF\s+",
        },
    },
    "printedsolid": {
        "ps_imports_": {
            "action": "strip",
            "name_pattern": r"^PS\s+Imports\s+",
        },
    },
    "smart_materials_3d": {
        "innovatefil_": {
            "action": "strip",
            "name_pattern": r"^Innovatefil\s+",
        },
        "ep_easy_print_": {
            "action": "strip",
            "name_pattern": r"^EP\s+Easy\s+Print\s+",
        },
    },
    "rosa3d_filaments": {
        "pet_g_standard_hs_": {
            "action": "strip",
            "name_pattern": r"^PET[\s_-]*G?\s*Standard\s+HS\s+",
        },
    },
    "amolen": {
        "glow_in_the_dark_": {
            "action": "strip",
            "name_pattern": r"^Glow\s+In\s+The\s+Dark\s+",
        },
    },
    "dremel": {
        "slk_cop_01_": {
            "action": "strip",
            "name_pattern": r"^SLK[\s_-]*COP[\s_-]*01\s*",
        },
        "nav_01_": {
            "action": "strip",
            "name_pattern": r"^NAV[\s_-]*01\s*",
        },
        "bla_01_": {
            "action": "strip",
            "name_pattern": r"^BLA[\s_-]*01\s*",
        },
    },
    "sainsmart": {
        "high_speed_95a_flexible_": {
            "action": "strip",
            "name_pattern": r"^High\s+Speed\s+95A\s+Flexible\s+",
        },
    },
    "sunlu": {
        "petg_glow_in_the_dark_": {
            "action": "strip",
            "name_pattern": r"^PETG\s+Glow\s+In\s+The\s+Dark\s+",
        },
        "pla_glow_in_the_dark_": {
            "action": "strip",
            "name_pattern": r"^PLA\s+Glow\s+In\s+The\s+Dark\s+",
        },
    },
}

# Product line prefixes at the variant level that need structural reorganization.
# These are moved into new filament directories named "{product_line}_{filament_id}".
# Prefixes are ordered longest-first within each brand to avoid partial matches.
PRODUCT_LINE_PREFIXES: dict[str, list[str]] = {
    "3dxtech": [
        "wearx_wear_resistant_nylon_filament_",
    ],
    "amolen": [
        "galaxy_sparkle_shiny_galaxy_", "90a_flexible_",
    ],
    "ataraxia_art": [
        "flexible_89a_",
    ],
    "dremel": [
        "digilab_eco_", "digilab_", "df",
    ],
    "eolas_prints": [
        "ingeo_850_", "ingeo_870_",
    ],
    "flashforge": [
        "chameleon_", "d_series_", "rapid_",
    ],
    "matter3d_inc": [
        "performance_",
    ],
    "polar_filament": [
        "biodegradable_flexible_95a_soft_",
    ],
    "polymaker": [
        "creator_special_edition_", "for_production_",
        "panchroma_", "polysmooth_", "polysonic_",
        "polylite_", "polycast_", "polywood_", "polymax_",
    ],
    "primacreator": [
        "primaselect_", "primavalue_", "easyprint_",
    ],
    "printedsolid": [
        "jessie_premium_",
    ],
    "recreus": [
        "conductive_filaflex_", "balena_filaflex_", "filaflex_",
    ],
    "rosa3d_filaments": [
        "impact_abrasive_uv_h2o_microbe_resistant_",
        "pet_g_structure_hs_", "pet_g_galaxy_hs_", "pet_g_hs_",
        "rosa_flex_",
    ],
    "sainsmart": [
        "temperature_sensitive_flexible_95a_",
        "flexible_95a_", "flexible_87a_", "gt_3_",
    ],
    "sunlu": [
        "luminous_glow_in_the_dark_",
    ],
}

# Additional SKU pattern to strip from variant names after removing the product line
# prefix.  Applied per-brand.  For dremel, the pattern after the prefix is typically
# "{color_abbrev}_{number}_" (e.g. "bla_01_") or just "{number}_{number}_" (e.g. "04_01_").
PRODUCT_LINE_SKU_PATTERNS: dict[str, str] = {
    "dremel": r"^(?:[a-z]+_)*(?:\d+_)+",
}

# Product line suffixes at the variant level that need structural reorganization.
# These are the suffix mirror of PRODUCT_LINE_PREFIXES: the suffix (minus leading
# underscore) becomes the product line, and the remainder is the color/variant.
# Suffixes are ordered longest-first within each brand.
PRODUCT_LINE_SUFFIXES: dict[str, list[str]] = {
    "coex_3d": [
        "_coexflex_60a", "_coexflex_60d", "_coexflex_40d", "_coexflex_30d",
    ],
    "sainsmart": ["_92a_flexible"],
    "zyltech": ["_texas_twister_series_multi_color"],
    "matterhackers": ["_mh_build_series_flexible"],
}

# Suffix noise to strip in-place (mirror of PREFIX_RULES but for suffixes).
SUFFIX_STRIP_RULES: dict[str, dict[str, dict[str, str]]] = {
    "zyltech": {
        "_new_made_in_usa_premium_composite": {
            "action": "strip",
            "name_pattern": r"\s*New\s+Made\s+In\s+Usa\s+Premium\s+Composite$",
        },
    },
    "matterhackers": {
        "_series_thermoplastic_polyurethane": {
            "action": "strip",
            "name_pattern": r"\s*Series\s+Thermoplastic\s+Polyurethane$",
        },
    },
}

# Regex patterns for Category 4 (technical specs in variant names)
TECH_SPEC_PATTERNS = [
    r"^\d+$",                     # bare number (e.g. RAL code "7016")
    r"hytrel_",                   # DuPont product codes
    r"coexflex_",                 # Coex product codes
    r"ingeo_\d+",                 # NatureWorks grade codes
    r"\d+a_flexible",             # hardness specs like "87a_flexible"
    r"flexible_\d+a_",            # hardness specs like "flexible_95a_"
    r"gt_\d+_high_speed_\d+a_",   # SainSmart GT model codes
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CleanupAction:
    """A single proposed fix."""
    category: int
    brand: str
    old_path: str       # relative to data/
    new_path: str       # relative to data/ (empty for report-only)
    description: str
    confidence: str     # "auto" or "manual_review"


@dataclass
class CleanupReport:
    """Aggregated cleanup results."""
    actions: list[CleanupAction] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    @property
    def auto_actions(self) -> list[CleanupAction]:
        return [a for a in self.actions if a.confidence == "auto"]

    @property
    def manual_actions(self) -> list[CleanupAction]:
        return [a for a in self.actions if a.confidence == "manual_review"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path: Path) -> Optional[dict[str, Any]]:
    """Load JSON from file with error handling."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return None


def save_json(path: Path, data: Any) -> None:
    """Save JSON with 2-space indent (matches project style)."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def slugify(text: str) -> str:
    """Convert text to a valid ID (lowercase, underscores)."""
    text = text.lower()
    text = re.sub(r"[-\s]+", "_", text)
    text = re.sub(r"[^a-z0-9_]", "", text)
    text = text.strip("_")
    text = re.sub(r"_+", "_", text)
    return text or "default"


def clean_display_name(slug: str) -> str:
    """Convert a slug to a display name. E.g. 'dark_blue' -> 'Dark Blue'."""
    return slug.replace("_", " ").title()


def is_color_like(name: str) -> bool:
    """Check if a directory name looks like a color."""
    parts = name.split("_")
    # Simple color: "blue", "red"
    if name in KNOWN_COLORS:
        return True
    # Modified color: "neon_cyan", "galaxy_blue", "dark_red"
    if len(parts) >= 2:
        modifier = parts[0]
        base = "_".join(parts[1:])
        if modifier in COLOR_MODIFIERS and base in KNOWN_COLORS:
            return True
    # Compound known colors: "mango_mojito", "liquid_luster", "kaoss_purple"
    if len(parts) >= 2 and parts[-1] in KNOWN_COLORS:
        if all(p in COLOR_MODIFIERS or p in KNOWN_COLORS for p in parts[:-1]):
            return True
    return False


def has_material_keyword(name: str) -> bool:
    """Check if a name contains material/product keywords."""
    parts = set(name.split("_"))
    return bool(parts & MATERIAL_KEYWORDS)


# ---------------------------------------------------------------------------
# Detection: Category 1 — Swapped filament/variant layers
# ---------------------------------------------------------------------------

def detect_category_1(data_dir: Path, brand: str, report: CleanupReport) -> list[tuple[Path, Path, str]]:
    """
    Detect filament dirs that are actually colors with variant dirs that are
    actually product names. Returns list of (source_filament_dir, target_filament_dir, color_name)
    for the apply phase.
    """
    moves: list[tuple[Path, Path, str]] = []
    brand_dir = data_dir / brand

    if not brand_dir.is_dir():
        return moves

    for material_dir in sorted(brand_dir.iterdir()):
        if not material_dir.is_dir() or material_dir.name.startswith("."):
            continue

        for filament_dir in sorted(material_dir.iterdir()):
            if not filament_dir.is_dir() or filament_dir.name.startswith("."):
                continue

            filament_id = filament_dir.name

            # Check: does this filament name look like a color?
            if not is_color_like(filament_id):
                continue

            # Check: do its variant subdirs look like product names?
            variant_dirs = [
                d for d in filament_dir.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            ]
            if not variant_dirs:
                continue

            product_variants = [
                d for d in variant_dirs
                if has_material_keyword(d.name)
            ]
            if not product_variants:
                continue

            # This filament dir is a color; its variants are product names.
            for variant_dir in product_variants:
                product_name = variant_dir.name
                target_filament_dir = material_dir / product_name
                color_name = filament_id

                rel_old = f"{brand}/{material_dir.name}/{filament_id}/{product_name}"
                rel_new = f"{brand}/{material_dir.name}/{product_name}/{color_name}"

                report.actions.append(CleanupAction(
                    category=1,
                    brand=brand,
                    old_path=rel_old,
                    new_path=rel_new,
                    description=f"Swap: filament '{filament_id}' is a color, "
                                f"variant '{product_name}' is a product",
                    confidence="auto",
                ))
                moves.append((filament_dir, target_filament_dir, color_name))

    return moves


def apply_category_1(data_dir: Path, moves: list[tuple[Path, Path, str]],
                      report: CleanupReport, dry_run: bool) -> None:
    """Execute Category 1 swaps."""
    # Group moves by target filament dir to handle merges.
    # Each source filament_dir (a color) may have multiple product-variant subdirs,
    # but usually just one. We need to:
    #   1. Create/ensure target filament dir exists
    #   2. Move the color as a variant subdir into it
    #   3. Clean up source

    # Track which source filament dirs have been fully processed so we can
    # clean them up after all moves.
    processed_sources: set[Path] = set()

    for source_filament_dir, target_filament_dir, color_name in moves:
        # The source_filament_dir is e.g. .../TPU/blue/
        # Inside it is a variant dir named like "flexible_tpu" that is actually the product.
        # target_filament_dir is e.g. .../TPU/flexible_tpu/
        # We want to create .../TPU/flexible_tpu/blue/ as a variant.

        target_variant_dir = target_filament_dir / color_name

        # Check for collision
        if target_variant_dir.exists():
            report.skipped.append(
                f"Cat 1: {target_variant_dir.relative_to(data_dir)} already exists, skipping"
            )
            continue

        if dry_run:
            processed_sources.add(source_filament_dir)
            continue

        # Ensure target filament dir exists
        target_filament_dir.mkdir(parents=True, exist_ok=True)

        # If target filament dir has no filament.json yet, create one from the
        # product-named variant dir (which has the real product data).
        target_filament_json = target_filament_dir / "filament.json"
        product_name = target_filament_dir.name

        if not target_filament_json.exists():
            # Try to get data from the source's variant dir (the product-named dir)
            source_product_dir = source_filament_dir / product_name
            source_variant_json = source_product_dir / "variant.json"
            source_filament_json = source_filament_dir / "filament.json"

            # Start with source filament.json data (has temperatures, density, etc.)
            filament_data = {}
            if source_filament_json.exists():
                loaded = load_json(source_filament_json)
                if loaded:
                    filament_data = loaded

            # Override id and name with the product name
            filament_data["id"] = product_name
            filament_data["name"] = clean_display_name(product_name)
            save_json(target_filament_json, filament_data)

        # Now move the color dir. We need to construct the variant from the
        # source filament dir itself (minus the product subdir).
        # The source looks like: .../TPU/blue/  (contains filament.json + flexible_tpu/)
        # We want: .../TPU/flexible_tpu/blue/  (contains variant.json + sizes.json)

        # The product-named subdir inside source may have variant.json and sizes.json
        # that actually belong to the color. Or the source filament dir itself may have
        # variant data. Let's check both.
        source_product_dir = source_filament_dir / product_name

        # Create the target variant directory
        target_variant_dir.mkdir(parents=True, exist_ok=True)

        # Move sizes.json if it exists in the product subdir
        for fname in ["sizes.json"]:
            src_file = source_product_dir / fname
            if src_file.exists():
                shutil.move(str(src_file), str(target_variant_dir / fname))

        # Create/update variant.json with the color info
        # Check if the product subdir had a variant.json with useful data (color_hex, traits)
        variant_data: dict[str, Any] = {}
        old_variant_json = source_product_dir / "variant.json"
        if old_variant_json.exists():
            loaded = load_json(old_variant_json)
            if loaded:
                # Keep color_hex, traits, etc. but fix id/name
                variant_data = loaded

        # Also check the source filament.json for color_hex (sometimes stored there)
        source_filament_json = source_filament_dir / "filament.json"
        if source_filament_json.exists():
            loaded = load_json(source_filament_json)
            if loaded and "color_hex" in loaded and "color_hex" not in variant_data:
                variant_data["color_hex"] = loaded["color_hex"]

        variant_data["id"] = color_name
        variant_data["name"] = clean_display_name(color_name)
        save_json(target_variant_dir / "variant.json", variant_data)

        # Clean up source product subdir (now empty or has just variant.json)
        if source_product_dir.exists():
            shutil.rmtree(str(source_product_dir))

        processed_sources.add(source_filament_dir)

    if dry_run:
        return

    # Clean up empty source filament dirs
    for source_dir in processed_sources:
        if source_dir.exists():
            # Remove filament.json and any remaining empty subdirs
            remaining = list(source_dir.iterdir())
            remaining_non_json = [
                f for f in remaining
                if f.is_dir() or f.name not in ("filament.json", "material.json")
            ]
            if not remaining_non_json:
                shutil.rmtree(str(source_dir))


# ---------------------------------------------------------------------------
# Detection + Apply: Categories 2 & 3 — Prefix stripping
# ---------------------------------------------------------------------------

def detect_and_apply_prefixes(data_dir: Path, brand: str, report: CleanupReport,
                               dry_run: bool, category_filter: Optional[int]) -> None:
    """Detect and optionally fix prefix pollution in variant names."""
    if brand not in PREFIX_RULES:
        return

    brand_dir = data_dir / brand
    if not brand_dir.is_dir():
        return

    rules = PREFIX_RULES[brand]

    for material_dir in sorted(brand_dir.iterdir()):
        if not material_dir.is_dir() or material_dir.name.startswith("."):
            continue

        for filament_dir in sorted(material_dir.iterdir()):
            if not filament_dir.is_dir() or filament_dir.name.startswith("."):
                continue

            # Collect existing variant names for collision detection
            existing_variants = {
                d.name for d in filament_dir.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            }

            for variant_dir in sorted(filament_dir.iterdir()):
                if not variant_dir.is_dir() or variant_dir.name.startswith("."):
                    continue

                variant_id = variant_dir.name

                for prefix, rule in rules.items():
                    if not variant_id.startswith(prefix):
                        continue

                    new_id = variant_id[len(prefix):]
                    if not new_id:
                        continue

                    cat = 2 if prefix != "ps_imports_" else 3
                    if category_filter is not None and category_filter != cat:
                        continue

                    is_auto = rule["action"] == "strip"
                    rel_old = f"{brand}/{material_dir.name}/{filament_dir.name}/{variant_id}"
                    rel_new = f"{brand}/{material_dir.name}/{filament_dir.name}/{new_id}"

                    # Collision check
                    if new_id in existing_variants and new_id != variant_id:
                        report.skipped.append(
                            f"Cat {cat}: {rel_old} -> {new_id} would collide "
                            f"with existing variant"
                        )
                        continue

                    report.actions.append(CleanupAction(
                        category=cat,
                        brand=brand,
                        old_path=rel_old,
                        new_path=rel_new if is_auto else "",
                        description=f"Strip prefix '{prefix}' from variant",
                        confidence="auto" if is_auto else "manual_review",
                    ))

                    if not is_auto:
                        break

                    # Track proposed rename for collision detection
                    existing_variants.discard(variant_id)
                    existing_variants.add(new_id)

                    if dry_run:
                        break

                    # Apply the rename
                    new_variant_dir = filament_dir / new_id
                    shutil.move(str(variant_dir), str(new_variant_dir))

                    # Update variant.json
                    variant_json_path = new_variant_dir / "variant.json"
                    if variant_json_path.exists():
                        data = load_json(variant_json_path)
                        if data:
                            data["id"] = new_id
                            # Clean the display name
                            old_name = data.get("name", "")
                            name_pattern = rule.get("name_pattern", "")
                            if name_pattern and old_name:
                                new_name = re.sub(name_pattern, "", old_name).strip()
                                # Clean up residual whitespace/dashes
                                new_name = re.sub(r"^\s*[-–—]\s*", "", new_name).strip()
                                if new_name:
                                    data["name"] = new_name
                                else:
                                    data["name"] = clean_display_name(new_id)
                            else:
                                data["name"] = clean_display_name(new_id)
                            save_json(variant_json_path, data)
                    break  # only one prefix match per variant


# ---------------------------------------------------------------------------
# Detection: Category 4 — Technical specs as variant names
# ---------------------------------------------------------------------------

def detect_category_4(data_dir: Path, brand: str, report: CleanupReport,
                       already_fixed: set[str]) -> None:
    """Flag variants with technical specs/product codes instead of color names."""
    brand_dir = data_dir / brand
    if not brand_dir.is_dir():
        return

    compiled_patterns = [re.compile(p) for p in TECH_SPEC_PATTERNS]

    for material_dir in sorted(brand_dir.iterdir()):
        if not material_dir.is_dir() or material_dir.name.startswith("."):
            continue

        for filament_dir in sorted(material_dir.iterdir()):
            if not filament_dir.is_dir() or filament_dir.name.startswith("."):
                continue

            for variant_dir in sorted(filament_dir.iterdir()):
                if not variant_dir.is_dir() or variant_dir.name.startswith("."):
                    continue

                variant_id = variant_dir.name
                rel = (f"{brand}/{material_dir.name}/"
                       f"{filament_dir.name}/{variant_id}")

                if rel in already_fixed:
                    continue

                for pattern in compiled_patterns:
                    if pattern.search(variant_id):
                        report.actions.append(CleanupAction(
                            category=4,
                            brand=brand,
                            old_path=rel,
                            new_path="",
                            description=f"Technical spec in variant name "
                                        f"(matched: {pattern.pattern})",
                            confidence="manual_review",
                        ))
                        break


# ---------------------------------------------------------------------------
# Detection: Category 6 — Overly long variant names
# ---------------------------------------------------------------------------

MAX_VARIANT_LENGTH = 40


def detect_category_6(data_dir: Path, brand: str, report: CleanupReport,
                       already_fixed: set[str]) -> None:
    """Flag variant names that are excessively long (post-fix audit)."""
    brand_dir = data_dir / brand
    if not brand_dir.is_dir():
        return

    for material_dir in sorted(brand_dir.iterdir()):
        if not material_dir.is_dir() or material_dir.name.startswith("."):
            continue

        for filament_dir in sorted(material_dir.iterdir()):
            if not filament_dir.is_dir() or filament_dir.name.startswith("."):
                continue

            for variant_dir in sorted(filament_dir.iterdir()):
                if not variant_dir.is_dir() or variant_dir.name.startswith("."):
                    continue

                variant_id = variant_dir.name
                if len(variant_id) <= MAX_VARIANT_LENGTH:
                    continue

                rel = (f"{brand}/{material_dir.name}/"
                       f"{filament_dir.name}/{variant_id}")

                # Skip if already reported by another category
                if rel in already_fixed:
                    continue

                report.actions.append(CleanupAction(
                    category=6,
                    brand=brand,
                    old_path=rel,
                    new_path="",
                    description=f"Variant name is {len(variant_id)} chars "
                                f"(max recommended: {MAX_VARIANT_LENGTH})",
                    confidence="manual_review",
                ))


# ---------------------------------------------------------------------------
# Detection + Apply: Category 7 — Product line prefix at variant level
# ---------------------------------------------------------------------------

def detect_and_apply_product_lines(data_dir: Path, brand: str,
                                    report: CleanupReport,
                                    dry_run: bool) -> None:
    """Move variants with product-line prefixes into new filament directories.

    For each matching variant the fix is:
      1. Strip the product-line prefix (and optional SKU codes) to get a clean
         color / variant name.
      2. Create a new filament directory named ``{product_line}_{filament_id}``.
      3. Move the variant directory into it.
      4. Write / update ``filament.json`` and ``variant.json``.
    """
    if brand not in PRODUCT_LINE_PREFIXES:
        return

    brand_dir = data_dir / brand
    if not brand_dir.is_dir():
        return

    prefixes = PRODUCT_LINE_PREFIXES[brand]
    sku_pattern = PRODUCT_LINE_SKU_PATTERNS.get(brand)
    sku_re = re.compile(sku_pattern) if sku_pattern else None

    # Track proposed target paths for dry-run collision detection.
    proposed_targets: set[str] = set()

    for material_dir in sorted(brand_dir.iterdir()):
        if not material_dir.is_dir() or material_dir.name.startswith("."):
            continue

        for filament_dir in sorted(material_dir.iterdir()):
            if not filament_dir.is_dir() or filament_dir.name.startswith("."):
                continue

            for variant_dir in sorted(filament_dir.iterdir()):
                if not variant_dir.is_dir() or variant_dir.name.startswith("."):
                    continue

                variant_id = variant_dir.name

                for prefix in prefixes:
                    if not variant_id.startswith(prefix):
                        continue

                    # Strip the product-line prefix
                    remainder = variant_id[len(prefix):]

                    # Strip optional SKU codes (e.g. dremel "bla_01_")
                    if sku_re:
                        m = sku_re.match(remainder)
                        if m:
                            remainder = remainder[m.end():]

                    if not remainder:
                        report.skipped.append(
                            f"Cat 7: {brand}/{material_dir.name}/"
                            f"{filament_dir.name}/{variant_id} "
                            f"-> empty after stripping prefix '{prefix}'"
                        )
                        break

                    # Compute the new filament directory
                    product_line = prefix.rstrip("_") or prefix
                    new_filament_id = f"{product_line}_{filament_dir.name}"
                    new_filament_dir = material_dir / new_filament_id
                    target_variant_dir = new_filament_dir / remainder

                    rel_old = (f"{brand}/{material_dir.name}/"
                               f"{filament_dir.name}/{variant_id}")
                    rel_new = (f"{brand}/{material_dir.name}/"
                               f"{new_filament_id}/{remainder}")

                    # Collision check (physical + proposed)
                    target_key = str(target_variant_dir)
                    if target_variant_dir.exists() or target_key in proposed_targets:
                        report.skipped.append(
                            f"Cat 7: {rel_old} -> {rel_new} would collide"
                        )
                        break

                    report.actions.append(CleanupAction(
                        category=7,
                        brand=brand,
                        old_path=rel_old,
                        new_path=rel_new,
                        description=(f"Move to product line filament "
                                     f"'{new_filament_id}'"),
                        confidence="auto",
                    ))

                    proposed_targets.add(target_key)

                    if dry_run:
                        break

                    # --- Apply the structural move ---

                    # Create new filament dir + filament.json
                    new_filament_dir.mkdir(parents=True, exist_ok=True)
                    new_filament_json = new_filament_dir / "filament.json"
                    if not new_filament_json.exists():
                        filament_data: dict[str, Any] = {}
                        source_fj = filament_dir / "filament.json"
                        if source_fj.exists():
                            loaded = load_json(source_fj)
                            if loaded:
                                filament_data = loaded.copy()
                        filament_data["id"] = new_filament_id
                        source_name = filament_data.get(
                            "name",
                            clean_display_name(filament_dir.name))
                        filament_data["name"] = (
                            f"{clean_display_name(product_line)} "
                            f"{source_name}")
                        save_json(new_filament_json, filament_data)

                    # Move variant directory
                    shutil.move(str(variant_dir), str(target_variant_dir))

                    # Update variant.json
                    variant_json = target_variant_dir / "variant.json"
                    if variant_json.exists():
                        data = load_json(variant_json)
                        if data:
                            data["id"] = remainder
                            data["name"] = clean_display_name(remainder)
                            save_json(variant_json, data)

                    break  # only one prefix match per variant


# ---------------------------------------------------------------------------
# Detection + Apply: Product line suffix at variant level
# ---------------------------------------------------------------------------

def detect_and_apply_product_line_suffixes(data_dir: Path, brand: str,
                                            report: CleanupReport,
                                            dry_run: bool) -> None:
    """Move variants with product-line suffixes into new filament directories.

    Mirror of detect_and_apply_product_lines but matches the end of variant
    names.  The suffix (minus leading underscore) becomes the product line,
    and the remainder before the suffix is the color/variant name.
    """
    if brand not in PRODUCT_LINE_SUFFIXES:
        return

    brand_dir = data_dir / brand
    if not brand_dir.is_dir():
        return

    suffixes = PRODUCT_LINE_SUFFIXES[brand]
    proposed_targets: set[str] = set()

    for material_dir in sorted(brand_dir.iterdir()):
        if not material_dir.is_dir() or material_dir.name.startswith("."):
            continue

        for filament_dir in sorted(material_dir.iterdir()):
            if not filament_dir.is_dir() or filament_dir.name.startswith("."):
                continue

            for variant_dir in sorted(filament_dir.iterdir()):
                if not variant_dir.is_dir() or variant_dir.name.startswith("."):
                    continue

                variant_id = variant_dir.name

                for suffix in suffixes:
                    if not variant_id.endswith(suffix):
                        continue

                    remainder = variant_id[: -len(suffix)]
                    if not remainder:
                        report.skipped.append(
                            f"Cat 7: {brand}/{material_dir.name}/"
                            f"{filament_dir.name}/{variant_id} "
                            f"-> empty after stripping suffix '{suffix}'"
                        )
                        break

                    product_line = suffix.lstrip("_") or suffix
                    new_filament_id = f"{product_line}_{filament_dir.name}"
                    new_filament_dir = material_dir / new_filament_id
                    target_variant_dir = new_filament_dir / remainder

                    rel_old = (f"{brand}/{material_dir.name}/"
                               f"{filament_dir.name}/{variant_id}")
                    rel_new = (f"{brand}/{material_dir.name}/"
                               f"{new_filament_id}/{remainder}")

                    target_key = str(target_variant_dir)
                    if target_variant_dir.exists() or target_key in proposed_targets:
                        report.skipped.append(
                            f"Cat 7: {rel_old} -> {rel_new} would collide"
                        )
                        break

                    report.actions.append(CleanupAction(
                        category=7,
                        brand=brand,
                        old_path=rel_old,
                        new_path=rel_new,
                        description=(f"Move to product line filament "
                                     f"'{new_filament_id}' (suffix)"),
                        confidence="auto",
                    ))

                    proposed_targets.add(target_key)

                    if dry_run:
                        break

                    # --- Apply the structural move ---
                    new_filament_dir.mkdir(parents=True, exist_ok=True)
                    new_filament_json = new_filament_dir / "filament.json"
                    if not new_filament_json.exists():
                        filament_data: dict[str, Any] = {}
                        source_fj = filament_dir / "filament.json"
                        if source_fj.exists():
                            loaded = load_json(source_fj)
                            if loaded:
                                filament_data = loaded.copy()
                        filament_data["id"] = new_filament_id
                        source_name = filament_data.get(
                            "name",
                            clean_display_name(filament_dir.name))
                        filament_data["name"] = (
                            f"{clean_display_name(product_line)} "
                            f"{source_name}")
                        save_json(new_filament_json, filament_data)

                    shutil.move(str(variant_dir), str(target_variant_dir))

                    variant_json = target_variant_dir / "variant.json"
                    if variant_json.exists():
                        data = load_json(variant_json)
                        if data:
                            data["id"] = remainder
                            data["name"] = clean_display_name(remainder)
                            save_json(variant_json, data)

                    break  # only one suffix match per variant


# ---------------------------------------------------------------------------
# Detection + Apply: Suffix stripping (in-place)
# ---------------------------------------------------------------------------

def detect_and_apply_suffix_strips(data_dir: Path, brand: str,
                                    report: CleanupReport,
                                    dry_run: bool) -> None:
    """Strip noise suffixes from variant names in-place."""
    if brand not in SUFFIX_STRIP_RULES:
        return

    brand_dir = data_dir / brand
    if not brand_dir.is_dir():
        return

    rules = SUFFIX_STRIP_RULES[brand]

    for material_dir in sorted(brand_dir.iterdir()):
        if not material_dir.is_dir() or material_dir.name.startswith("."):
            continue

        for filament_dir in sorted(material_dir.iterdir()):
            if not filament_dir.is_dir() or filament_dir.name.startswith("."):
                continue

            existing_variants = {
                d.name for d in filament_dir.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            }

            for variant_dir in sorted(filament_dir.iterdir()):
                if not variant_dir.is_dir() or variant_dir.name.startswith("."):
                    continue

                variant_id = variant_dir.name

                for suffix, rule in rules.items():
                    if not variant_id.endswith(suffix):
                        continue

                    new_id = variant_id[: -len(suffix)]
                    if not new_id:
                        continue

                    rel_old = f"{brand}/{material_dir.name}/{filament_dir.name}/{variant_id}"
                    rel_new = f"{brand}/{material_dir.name}/{filament_dir.name}/{new_id}"

                    if new_id in existing_variants and new_id != variant_id:
                        report.skipped.append(
                            f"Cat 2: {rel_old} -> {new_id} would collide "
                            f"with existing variant"
                        )
                        continue

                    report.actions.append(CleanupAction(
                        category=2,
                        brand=brand,
                        old_path=rel_old,
                        new_path=rel_new,
                        description=f"Strip suffix '{suffix}' from variant",
                        confidence="auto",
                    ))

                    existing_variants.discard(variant_id)
                    existing_variants.add(new_id)

                    if dry_run:
                        break

                    new_variant_dir = filament_dir / new_id
                    shutil.move(str(variant_dir), str(new_variant_dir))

                    variant_json_path = new_variant_dir / "variant.json"
                    if variant_json_path.exists():
                        data = load_json(variant_json_path)
                        if data:
                            data["id"] = new_id
                            old_name = data.get("name", "")
                            name_pattern = rule.get("name_pattern", "")
                            if name_pattern and old_name:
                                new_name = re.sub(name_pattern, "", old_name).strip()
                                if new_name:
                                    data["name"] = new_name
                                else:
                                    data["name"] = clean_display_name(new_id)
                            else:
                                data["name"] = clean_display_name(new_id)
                            save_json(variant_json_path, data)
                    break  # only one suffix match per variant


# ---------------------------------------------------------------------------
# Detection + Apply: Category 5 — Color split
# ---------------------------------------------------------------------------

def detect_and_apply_color_split(data_dir: Path, brand: str,
                                  report: CleanupReport,
                                  dry_run: bool) -> None:
    """Split filament dirs whose name contains both a product type and a color.

    E.g. silk_pla_red -> silk_pla/red (filament dir / variant dir).
    """
    brand_dir = data_dir / brand
    if not brand_dir.is_dir():
        return

    for material_dir in sorted(brand_dir.iterdir()):
        if not material_dir.is_dir() or material_dir.name.startswith("."):
            continue

        # Collect filament dirs up front since we'll be modifying the directory
        filament_dirs = sorted([
            d for d in material_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ])

        for filament_dir in filament_dirs:
            filament_id = filament_dir.name
            parts = filament_id.split("_")

            matched_head = None
            matched_tail = None

            for i in range(1, min(3, len(parts))):
                tail = "_".join(parts[-i:])
                head = "_".join(parts[:-i])
                if tail in KNOWN_COLORS and head and has_material_keyword(head):
                    matched_head = head
                    matched_tail = tail
                    break

            if not matched_head:
                continue

            rel_old = f"{brand}/{material_dir.name}/{filament_id}"
            target_filament_dir = material_dir / matched_head
            target_variant_dir = target_filament_dir / matched_tail

            rel_new = f"{brand}/{material_dir.name}/{matched_head}/{matched_tail}"

            if target_variant_dir.exists():
                report.skipped.append(
                    f"Cat 5: {rel_old} -> {rel_new} would collide"
                )
                continue

            report.actions.append(CleanupAction(
                category=5,
                brand=brand,
                old_path=rel_old,
                new_path=rel_new,
                description=f"Split filament '{filament_id}' into "
                            f"'{matched_head}/{matched_tail}'",
                confidence="auto",
            ))

            if dry_run:
                continue

            # --- Apply the color split ---

            # Create target filament dir
            target_filament_dir.mkdir(parents=True, exist_ok=True)

            # Copy/create filament.json for the target
            target_filament_json = target_filament_dir / "filament.json"
            if not target_filament_json.exists():
                filament_data: dict[str, Any] = {}
                source_fj = filament_dir / "filament.json"
                if source_fj.exists():
                    loaded = load_json(source_fj)
                    if loaded:
                        filament_data = loaded.copy()
                filament_data["id"] = matched_head
                filament_data["name"] = clean_display_name(matched_head)
                # Remove color_hex from filament level (belongs on variant)
                color_hex = filament_data.pop("color_hex", None)
                save_json(target_filament_json, filament_data)
            else:
                # Read color_hex from source for the variant
                color_hex = None
                source_fj = filament_dir / "filament.json"
                if source_fj.exists():
                    loaded = load_json(source_fj)
                    if loaded:
                        color_hex = loaded.get("color_hex")

            # Create variant dir
            target_variant_dir.mkdir(parents=True, exist_ok=True)

            # Build variant.json
            variant_data: dict[str, Any] = {
                "id": matched_tail,
                "name": clean_display_name(matched_tail),
            }
            if color_hex:
                variant_data["color_hex"] = color_hex
            save_json(target_variant_dir / "variant.json", variant_data)

            # Move sizes.json if exists
            sizes_json = filament_dir / "sizes.json"
            if sizes_json.exists():
                shutil.move(str(sizes_json), str(target_variant_dir / "sizes.json"))

            # Move any variant subdirs from old filament to target filament
            for sub in sorted(filament_dir.iterdir()):
                if sub.is_dir() and not sub.name.startswith("."):
                    target_sub = target_filament_dir / sub.name
                    if not target_sub.exists():
                        shutil.move(str(sub), str(target_sub))

            # Clean up old filament dir
            remaining = [f for f in filament_dir.iterdir()
                         if f.name not in ("filament.json", "material.json")]
            if not any(f.is_dir() for f in remaining):
                shutil.rmtree(str(filament_dir))


# ---------------------------------------------------------------------------
# Helpers for Category 8
# ---------------------------------------------------------------------------

# Material keywords that should be UPPERCASED in display names.
_MATERIAL_UPPER = {
    "pla", "petg", "abs", "asa", "tpu", "tpe", "pa", "pa6", "pa12",
    "pc", "pva", "hips", "pctg", "pvdf", "pom", "peek", "pei", "pet",
    "pps", "ppa", "pvb", "pbt", "cf", "gf", "ht", "uv", "hs",
}


def id_to_display_name(slug: str) -> str:
    """Convert a filament/variant slug to a proper display name.

    Material keywords are uppercased; everything else is title-cased.
    E.g. ``95a_tpu`` -> ``95A TPU``, ``high_speed_pla`` -> ``High Speed PLA``.
    """
    parts = slug.split("_")
    result = []
    for p in parts:
        if p.lower() in _MATERIAL_UPPER:
            result.append(p.upper())
        else:
            result.append(p.title())
    return " ".join(result)


def compute_common_prefix(names: list[str]) -> str:
    """Return the longest common prefix ending in ``_`` shared by all *names*.

    Returns an empty string when no qualifying prefix exists.
    """
    if not names:
        return ""
    prefix = names[0]
    for name in names[1:]:
        while not name.startswith(prefix):
            prefix = prefix[:-1]
            if not prefix:
                return ""
    # Truncate to the last underscore so the prefix is a complete "word_"
    idx = prefix.rfind("_")
    if idx > 0:
        return prefix[: idx + 1]
    return ""


def prefix_implied_by_filament(prefix: str, filament_id: str, brand: str) -> bool:
    """Return True if the prefix information is already captured by the hierarchy.

    When True the fix is a simple in-place rename (strip); when False the fix
    is a structural move to a new filament directory.
    """
    p = prefix.rstrip("_")

    # Direct containment: "metallic" in "metallic_pla"
    if p in filament_id:
        return True

    # Abbreviation: "hs" for "high_speed"
    if p == "hs" and "high_speed" in filament_id:
        return True
    if p == "high_speed" and "high_speed" in filament_id:
        return True

    # Material re-spelling: "pet_g" for "petg", "matt_pet_g" for "matte_petg"
    if p.replace("_", "") in filament_id.replace("_", ""):
        return True

    # Glow patterns: "glow_in_the_dark" or "starter_glow_in_the_dark" for "glow_*"
    if "glow_in_the_dark" in prefix and "glow" in filament_id:
        return True

    # Brand name present in prefix: "voxel_hs" contains "voxel" from "voxel_pla"
    brand_parts = set(brand.split("_"))
    prefix_parts = set(p.split("_"))
    if brand_parts & prefix_parts:
        return True

    return False


# ---------------------------------------------------------------------------
# Detection + Apply: Category 8 — Universal common-prefix detection
# ---------------------------------------------------------------------------

def detect_and_apply_common_prefix(data_dir: Path, brand: str,
                                    report: CleanupReport,
                                    dry_run: bool) -> None:
    """Detect filament types where ALL variants share a common prefix.

    * If the prefix is already implied by the filament type name (or brand
      name), the variants are renamed in-place (prefix stripped).
    * Otherwise, a new filament directory is created incorporating the prefix,
      and the variants are moved into it.
    """
    brand_dir = data_dir / brand
    if not brand_dir.is_dir():
        return

    for material_dir in sorted(brand_dir.iterdir()):
        if not material_dir.is_dir() or material_dir.name.startswith("."):
            continue

        # Snapshot filament dirs (we may add new ones during iteration).
        filament_dirs = sorted([
            d for d in material_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ])

        for filament_dir in filament_dirs:
            variant_dirs = sorted([
                d for d in filament_dir.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            ])

            if len(variant_dirs) < 2:
                continue

            variant_names = [d.name for d in variant_dirs]
            cp = compute_common_prefix(variant_names)

            if not cp or len(cp) < 3:
                continue

            # Verify ALL variants truly share the prefix.
            if not all(v.startswith(cp) for v in variant_names):
                continue

            filament_id = filament_dir.name
            implied = prefix_implied_by_filament(cp, filament_id, brand)

            if implied:
                # --- Strip in-place ---
                _apply_strip(data_dir, brand, material_dir, filament_dir,
                             variant_dirs, cp, report, dry_run)
            else:
                # --- Structural move to new filament type ---
                _apply_move(data_dir, brand, material_dir, filament_dir,
                            variant_dirs, cp, report, dry_run)


def _apply_strip(data_dir: Path, brand: str, material_dir: Path,
                  filament_dir: Path, variant_dirs: list[Path],
                  prefix: str, report: CleanupReport, dry_run: bool) -> None:
    """Strip *prefix* from all variant dirs under *filament_dir* in-place."""
    existing = {d.name for d in variant_dirs}

    for variant_dir in variant_dirs:
        old_id = variant_dir.name
        new_id = old_id[len(prefix):]
        if not new_id:
            continue

        rel_old = (f"{brand}/{material_dir.name}/"
                   f"{filament_dir.name}/{old_id}")
        rel_new = (f"{brand}/{material_dir.name}/"
                   f"{filament_dir.name}/{new_id}")

        # Collision check
        if new_id in existing and new_id != old_id:
            report.skipped.append(
                f"Cat 8: {rel_old} -> {new_id} would collide"
            )
            continue

        report.actions.append(CleanupAction(
            category=8,
            brand=brand,
            old_path=rel_old,
            new_path=rel_new,
            description=f"Strip common prefix '{prefix}'",
            confidence="auto",
        ))

        existing.discard(old_id)
        existing.add(new_id)

        if dry_run:
            continue

        new_variant_dir = filament_dir / new_id
        shutil.move(str(variant_dir), str(new_variant_dir))

        # Update variant.json
        variant_json = new_variant_dir / "variant.json"
        if variant_json.exists():
            data = load_json(variant_json)
            if data:
                data["id"] = new_id
                data["name"] = _clean_variant_name(
                    data.get("name", ""), prefix, new_id)
                save_json(variant_json, data)


def _apply_move(data_dir: Path, brand: str, material_dir: Path,
                 filament_dir: Path, variant_dirs: list[Path],
                 prefix: str, report: CleanupReport, dry_run: bool) -> None:
    """Move variants into a new filament dir named ``{prefix}{filament_id}``."""
    filament_id = filament_dir.name
    product_line = prefix.rstrip("_")
    new_filament_id = f"{product_line}_{filament_id}"
    new_filament_dir = material_dir / new_filament_id

    # Track proposed targets for collision detection.
    proposed: set[str] = set()

    for variant_dir in variant_dirs:
        old_id = variant_dir.name
        new_id = old_id[len(prefix):]
        if not new_id:
            report.skipped.append(
                f"Cat 8: {brand}/{material_dir.name}/"
                f"{filament_id}/{old_id} -> empty after stripping '{prefix}'"
            )
            continue

        target_variant_dir = new_filament_dir / new_id

        rel_old = (f"{brand}/{material_dir.name}/"
                   f"{filament_id}/{old_id}")
        rel_new = (f"{brand}/{material_dir.name}/"
                   f"{new_filament_id}/{new_id}")

        target_key = str(target_variant_dir)
        if target_variant_dir.exists() or target_key in proposed:
            report.skipped.append(
                f"Cat 8: {rel_old} -> {rel_new} would collide"
            )
            continue

        report.actions.append(CleanupAction(
            category=8,
            brand=brand,
            old_path=rel_old,
            new_path=rel_new,
            description=(f"Move to new filament '{new_filament_id}', "
                         f"strip prefix '{prefix}'"),
            confidence="auto",
        ))

        proposed.add(target_key)

        if dry_run:
            continue

        # Create new filament dir + filament.json on first encounter.
        new_filament_dir.mkdir(parents=True, exist_ok=True)
        new_filament_json = new_filament_dir / "filament.json"
        if not new_filament_json.exists():
            filament_data: dict[str, Any] = {}
            source_fj = filament_dir / "filament.json"
            if source_fj.exists():
                loaded = load_json(source_fj)
                if loaded:
                    filament_data = loaded.copy()
            filament_data["id"] = new_filament_id
            filament_data["name"] = id_to_display_name(new_filament_id)
            save_json(new_filament_json, filament_data)

        # Move variant directory.
        shutil.move(str(variant_dir), str(target_variant_dir))

        # Update variant.json
        variant_json = target_variant_dir / "variant.json"
        if variant_json.exists():
            data = load_json(variant_json)
            if data:
                data["id"] = new_id
                data["name"] = _clean_variant_name(
                    data.get("name", ""), prefix, new_id)
                save_json(variant_json, data)

    if dry_run:
        return

    # If the original filament dir lost ALL its variant subdirs, clean it up.
    remaining_variants = [
        d for d in filament_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ]
    if not remaining_variants and filament_dir.exists():
        shutil.rmtree(str(filament_dir))


def _clean_variant_name(old_name: str, prefix: str, new_id: str) -> str:
    """Derive a clean display name for a variant after prefix stripping.

    Tries to intelligently clean the old name first; falls back to generating
    from the new ID slug.
    """
    # Remove empty parentheses left by OPT import first.
    cleaned = re.sub(r"\(\s*\)", "", old_name).strip()

    # Build a regex from the prefix slug.  Each underscore becomes a flexible
    # separator matching whitespace, underscores, hyphens, and stray
    # non-alphanumeric chars (like "+").
    sep = r"[\s_+\-.*]*"
    parts = prefix.rstrip("_").split("_")
    pattern_str = r"^" + sep.join(re.escape(p) for p in parts) + sep
    cleaned = re.sub(pattern_str, "", cleaned, flags=re.IGNORECASE).strip()

    # Collapse multiple spaces.
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()

    if cleaned:
        return cleaned

    # Fallback: generate from slug.
    return clean_display_name(new_id)


# ---------------------------------------------------------------------------
# Detection + Apply: Category 9 — Broken display names
# ---------------------------------------------------------------------------

def detect_and_apply_name_fixes(data_dir: Path, brand: str,
                                 report: CleanupReport,
                                 dry_run: bool) -> None:
    """Fix broken display names in variant.json files.

    Targets:
    * Empty parentheses ``()``
    * Double/triple spaces
    * Leading/trailing whitespace
    """
    brand_dir = data_dir / brand
    if not brand_dir.is_dir():
        return

    for material_dir in sorted(brand_dir.iterdir()):
        if not material_dir.is_dir() or material_dir.name.startswith("."):
            continue

        for filament_dir in sorted(material_dir.iterdir()):
            if not filament_dir.is_dir() or filament_dir.name.startswith("."):
                continue

            for variant_dir in sorted(filament_dir.iterdir()):
                if not variant_dir.is_dir() or variant_dir.name.startswith("."):
                    continue

                variant_json = variant_dir / "variant.json"
                if not variant_json.exists():
                    continue

                data = load_json(variant_json)
                if not data:
                    continue

                name = data.get("name", "")
                if not name:
                    continue

                new_name = name

                # Remove empty parentheses.
                new_name = re.sub(r"\(\s*\)", "", new_name)

                # Collapse multiple spaces.
                new_name = re.sub(r"\s{2,}", " ", new_name)

                # Strip leading/trailing whitespace.
                new_name = new_name.strip()

                if not new_name:
                    new_name = clean_display_name(variant_dir.name)

                # Detect leftover prefix content: if the name is
                # significantly longer than what the ID would produce
                # and ends with the ID-based name, strip the extra.
                expected = clean_display_name(variant_dir.name)
                if (new_name != expected
                        and new_name.lower().endswith(expected.lower())
                        and len(new_name) > len(expected) + 2):
                    new_name = expected

                if new_name == name:
                    continue

                rel = (f"{brand}/{material_dir.name}/"
                       f"{filament_dir.name}/{variant_dir.name}")

                report.actions.append(CleanupAction(
                    category=9,
                    brand=brand,
                    old_path=rel,
                    new_path="",
                    description=f"Fix display name: '{name}' -> '{new_name}'",
                    confidence="auto",
                ))

                if dry_run:
                    continue

                data["name"] = new_name
                save_json(variant_json, data)


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

def format_report(report: CleanupReport, applied: bool) -> str:
    """Format the cleanup report as human-readable text."""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("OPT NAMING CLEANUP REPORT")
    lines.append("=" * 60)
    lines.append("")

    mode = "APPLIED" if applied else "DRY RUN (use --apply to execute)"
    lines.append(f"Mode: {mode}")
    lines.append("")

    # Group auto actions by category
    auto = report.auto_actions
    manual = report.manual_actions

    if auto:
        lines.append("-" * 60)
        lines.append(f"AUTO-FIXABLE ({len(auto)}):")
        lines.append("-" * 60)

        for cat in sorted({a.category for a in auto}):
            cat_actions = [a for a in auto if a.category == cat]
            cat_labels = {
                1: "Swapped filament/variant layers",
                2: "Prefix/suffix stripped",
                3: "Import prefix stripped",
                5: "Color split from filament name",
                7: "Product line moved to filament dir",
                8: "Common prefix stripped/moved",
                9: "Display name fixed",
            }
            label = cat_labels.get(cat, f"Category {cat}")
            lines.append(f"\n  Category {cat} - {label} ({len(cat_actions)}):")
            for a in cat_actions:
                if a.new_path:
                    lines.append(f"    {a.old_path}")
                    lines.append(f"      -> {a.new_path}")
                else:
                    lines.append(f"    {a.old_path}")
        lines.append("")

    if manual:
        lines.append("-" * 60)
        lines.append(f"MANUAL REVIEW NEEDED ({len(manual)}):")
        lines.append("-" * 60)

        for cat in sorted({a.category for a in manual}):
            cat_actions = [a for a in manual if a.category == cat]
            cat_labels = {
                2: "Series prefix (potential product line)",
                3: "Import prefix (potential product line)",
                4: "Technical specs in variant names",
                5: "Colors merged into filament names",
                6: "Overly long variant names",
                7: "Product line prefix at variant level",
            }
            label = cat_labels.get(cat, f"Category {cat}")
            lines.append(f"\n  Category {cat} - {label} ({len(cat_actions)}):")
            for a in cat_actions:
                lines.append(f"    {a.old_path}")
                lines.append(f"      Reason: {a.description}")
        lines.append("")

    if report.skipped:
        lines.append("-" * 60)
        lines.append(f"SKIPPED DUE TO COLLISIONS ({len(report.skipped)}):")
        lines.append("-" * 60)
        for s in report.skipped:
            lines.append(f"    {s}")
        lines.append("")

    if report.errors:
        lines.append("-" * 60)
        lines.append(f"ERRORS ({len(report.errors)}):")
        lines.append("-" * 60)
        for e in report.errors:
            lines.append(f"    {e}")
        lines.append("")

    # Summary
    lines.append("-" * 60)
    lines.append("SUMMARY:")
    lines.append(f"  Auto-fixable:   {len(auto)}")
    lines.append(f"  Manual review:  {len(manual)}")
    lines.append(f"  Skipped:        {len(report.skipped)}")
    lines.append(f"  Errors:         {len(report.errors)}")
    lines.append(f"  Total issues:   {len(report.actions)}")
    lines.append("=" * 60)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main script
# ---------------------------------------------------------------------------

@register_script
class CleanupOptNamingScript(BaseScript):
    name = "cleanup_opt_naming"
    description = "Fix naming issues from the OpenPrintTag import"

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--apply", action="store_true",
            help="Actually apply fixes (default is dry-run)",
        )
        parser.add_argument(
            "--brand", type=str, default=None,
            help="Only process a specific brand (by folder name)",
        )
        parser.add_argument(
            "--category", type=int, choices=[1, 2, 3, 4, 5, 6, 7, 8, 9], default=None,
            help="Only process a specific category of issues",
        )
        parser.add_argument(
            "--report-path", type=str,
            default=".cache/opt-cleanup-report.txt",
            help="Path to save the cleanup report",
        )

    def run(self, args: argparse.Namespace) -> ScriptResult:
        dry_run = not args.apply
        category_filter = args.category
        report = CleanupReport()

        # Determine which brands to process
        if args.brand:
            brands = [args.brand]
        else:
            brands = sorted([
                d.name for d in self.data_dir.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            ])

        total = len(brands)
        for i, brand in enumerate(brands):
            self.emit_progress("scanning", int((i / total) * 100), f"Scanning {brand}")

            # Category 1: Swapped layers (auto-fix)
            if category_filter is None or category_filter == 1:
                moves = detect_category_1(self.data_dir, brand, report)
                if not dry_run and moves:
                    apply_category_1(self.data_dir, moves, report, dry_run=False)

            # Categories 2 & 3: Prefix stripping (auto-fix)
            if category_filter is None or category_filter in (2, 3):
                detect_and_apply_prefixes(
                    self.data_dir, brand, report, dry_run, category_filter
                )

            # Category 7: Product line prefix reorganization (auto-fix)
            if category_filter is None or category_filter == 7:
                detect_and_apply_product_lines(
                    self.data_dir, brand, report, dry_run
                )

            # Category 7 (suffix): Product line suffix reorganization (auto-fix)
            if category_filter is None or category_filter == 7:
                detect_and_apply_product_line_suffixes(
                    self.data_dir, brand, report, dry_run
                )

            # Suffix stripping (auto-fix, reported as Cat 2)
            if category_filter is None or category_filter == 2:
                detect_and_apply_suffix_strips(
                    self.data_dir, brand, report, dry_run
                )

            # Category 5: Color split from filament names (auto-fix)
            if category_filter is None or category_filter == 5:
                detect_and_apply_color_split(
                    self.data_dir, brand, report, dry_run
                )

            # Category 8: Universal common-prefix detection (auto-fix)
            if category_filter is None or category_filter == 8:
                detect_and_apply_common_prefix(
                    self.data_dir, brand, report, dry_run
                )

            # Category 9: Broken display names (auto-fix)
            if category_filter is None or category_filter == 9:
                detect_and_apply_name_fixes(
                    self.data_dir, brand, report, dry_run
                )

        # Collect already-reported paths for dedup in Cat 4 & 6
        already_reported = {a.old_path for a in report.actions}
        already_reported.update(a.new_path for a in report.actions if a.new_path)

        # Category 4: Technical specs (report only for leftovers)
        if category_filter is None or category_filter == 4:
            for brand in brands:
                detect_category_4(self.data_dir, brand, report, already_reported)

        # Category 6: Long names (post-fix audit, runs over current state)
        if category_filter is None or category_filter == 6:
            for brand in brands:
                detect_category_6(self.data_dir, brand, report, already_reported)

        self.emit_progress("report", 100, "Generating report")

        # Format and save report
        report_text = format_report(report, applied=not dry_run)
        self.log(report_text)

        report_path = Path(args.report_path)
        if not report_path.is_absolute():
            report_path = self.project_root / report_path
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_text, encoding="utf-8")

        auto_count = len(report.auto_actions)
        manual_count = len(report.manual_actions)

        if dry_run:
            msg = (f"Dry run complete. {auto_count} auto-fixable, "
                   f"{manual_count} need manual review. "
                   f"Report saved to {report_path}")
        else:
            msg = (f"Applied {auto_count} fixes. "
                   f"{manual_count} still need manual review. "
                   f"Report saved to {report_path}")

        return ScriptResult(
            success=True,
            message=msg,
            data={
                "auto_fixed": auto_count,
                "manual_review": manual_count,
                "skipped": len(report.skipped),
                "errors": len(report.errors),
                "report_path": str(report_path),
            },
        )

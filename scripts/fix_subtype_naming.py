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

    # =========================================================================
    # 3djake PETG
    # =========================================================================
    {
        "manufacturer": "3djake",
        "material": "PETG",
        "source_subtype": "petg",
        "id_prefix": "easy_",
        "name_prefix": ["easy "],
        "target_subtype": "easy_petg",
        "target_display_name": "easy PETG",
    },

    # =========================================================================
    # Formfutura PLA/pla - 9 product lines
    # NOTE: easyfil_e_ MUST come before easyfil_ (longer prefix first)
    # =========================================================================
    {
        "manufacturer": "formfutura",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "easyfil_e_",
        "name_prefix": ["EasyFil e "],
        "target_subtype": "easyfil_e_pla",
        "target_display_name": "EasyFil e PLA",
    },
    {
        "manufacturer": "formfutura",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "easyfil_",
        "name_prefix": ["EasyFil  ", "EasyFil "],
        "target_subtype": "easyfil_pla",
        "target_display_name": "EasyFil PLA",
    },
    {
        "manufacturer": "formfutura",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "galaxy_",
        "name_prefix": ["Galaxy  ", "Galaxy "],
        "target_subtype": "galaxy_pla",
        "target_display_name": "Galaxy PLA",
    },
    {
        "manufacturer": "formfutura",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "premium_",
        "name_prefix": ["Premium  ", "Premium "],
        "target_subtype": "premium_pla",
        "target_display_name": "Premium PLA",
    },
    {
        "manufacturer": "formfutura",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "high_precision_",
        "name_prefix": ["High Precision  ", "High Precision "],
        "target_subtype": "high_precision_pla",
        "target_display_name": "High Precision PLA",
    },
    {
        "manufacturer": "formfutura",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "reform_r_",
        "name_prefix": ["ReForm \u2013 r ", "ReForm - r ", "ReForm r "],
        "target_subtype": "reform_r_pla",
        "target_display_name": "ReForm r PLA",
    },
    {
        "manufacturer": "formfutura",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "easywood_",
        "name_prefix": ["EasyWood "],
        "target_subtype": "easywood_pla",
        "target_display_name": "EasyWood PLA",
    },
    {
        "manufacturer": "formfutura",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "stonefil_",
        "name_prefix": ["StoneFil "],
        "target_subtype": "stonefil_pla",
        "target_display_name": "StoneFil PLA",
    },
    {
        "manufacturer": "formfutura",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "metalfil_",
        "name_prefix": ["MetalFil \u2013 ", "MetalFil - ", "MetalFil "],
        "target_subtype": "metalfil_pla",
        "target_display_name": "MetalFil PLA",
    },

    # =========================================================================
    # Formfutura ABS/abs
    # =========================================================================
    {
        "manufacturer": "formfutura",
        "material": "ABS",
        "source_subtype": "abs",
        "id_prefix": "reform_rtitan_",
        "name_prefix": ["ReForm \u2013 rTitan ", "ReForm - rTitan ", "ReForm rTitan "],
        "target_subtype": "reform_rtitan_abs",
        "target_display_name": "ReForm rTitan ABS",
    },
    {
        "manufacturer": "formfutura",
        "material": "ABS",
        "source_subtype": "abs",
        "id_prefix": "easyfil_",
        "name_prefix": ["EasyFil  ", "EasyFil "],
        "target_subtype": "easyfil_abs",
        "target_display_name": "EasyFil ABS",
    },
    {
        "manufacturer": "formfutura",
        "material": "ABS",
        "source_subtype": "abs",
        "id_prefix": "titanx_",
        "name_prefix": ["TitanX "],
        "target_subtype": "titanx_abs",
        "target_display_name": "TitanX ABS",
    },
    {
        "manufacturer": "formfutura",
        "material": "ABS",
        "source_subtype": "abs",
        "id_prefix": "flame_retardant_",
        "name_prefix": ["Flame Retardant "],
        "target_subtype": "flame_retardant_abs",
        "target_display_name": "Flame Retardant ABS",
    },

    # =========================================================================
    # Formfutura PET/pet
    # =========================================================================
    {
        "manufacturer": "formfutura",
        "material": "PET",
        "source_subtype": "pet",
        "id_prefix": "reform_r_",
        "name_prefix": ["ReForm \u2013 r ", "ReForm - r ", "ReForm r "],
        "target_subtype": "reform_r_pet",
        "target_display_name": "ReForm r PET",
    },
    {
        "manufacturer": "formfutura",
        "material": "PET",
        "source_subtype": "pet",
        "id_prefix": "high_precision_",
        "name_prefix": ["High Precision  ", "High Precision "],
        "target_subtype": "high_precision_pet",
        "target_display_name": "High Precision PET",
    },

    # =========================================================================
    # Formfutura PLA/matte_pla
    # =========================================================================
    {
        "manufacturer": "formfutura",
        "material": "PLA",
        "source_subtype": "matte_pla",
        "id_prefix": "easyfil_e_matt_",
        "name_prefix": ["EasyFil e Matt "],
        "target_subtype": "easyfil_e_matte_pla",
        "target_display_name": "EasyFil e Matte PLA",
    },
    {
        "manufacturer": "formfutura",
        "material": "PLA",
        "source_subtype": "matte_pla",
        "id_prefix": "volcano_",
        "name_prefix": ["Volcano  ", "Volcano "],
        "target_subtype": "volcano_matte_pla",
        "target_display_name": "Volcano Matte PLA",
    },

    # =========================================================================
    # FilamentPM PLA/pla (names use quoted color names)
    # =========================================================================
    {
        "manufacturer": "filamentpm",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "extrafill_",
        "name_prefix": ["Extrafill "],
        "target_subtype": "extrafill_pla",
        "target_display_name": "Extrafill PLA",
    },
    {
        "manufacturer": "filamentpm",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "timberfill_",
        "name_prefix": ["Timberfill\u00ae ", "Timberfill "],
        "target_subtype": "timberfill_pla",
        "target_display_name": "Timberfill PLA",
    },
    {
        "manufacturer": "filamentpm",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "crystal_clear_",
        "name_prefix": ["Crystal Clear "],
        "target_subtype": "crystal_clear_pla",
        "target_display_name": "Crystal Clear PLA",
    },
    {
        "manufacturer": "filamentpm",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "skin_edition_",
        "name_prefix": ["Skin edition - ", "skin edition - "],
        "target_subtype": "skin_edition_pla",
        "target_display_name": "Skin Edition PLA",
    },
    {
        "manufacturer": "filamentpm",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "pastel_edition_",
        "name_prefix": ["pastel edition - ", "Pastel edition - ", "Pastel Edition - "],
        "target_subtype": "pastel_edition_pla",
        "target_display_name": "Pastel Edition PLA",
    },
    {
        "manufacturer": "filamentpm",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "army_edition_",
        "name_prefix": ["Army edition - ", "army edition - ", "Army Edition - "],
        "target_subtype": "army_edition_pla",
        "target_display_name": "Army Edition PLA",
    },
    {
        "manufacturer": "filamentpm",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "pearl_",
        "name_prefix": ["Pearl "],
        "target_subtype": "pearl_pla",
        "target_display_name": "Pearl PLA",
    },
    {
        "manufacturer": "filamentpm",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "marblejet_",
        "name_prefix": ["MarbleJet - ", "MarbleJet "],
        "target_subtype": "marblejet_pla",
        "target_display_name": "MarbleJet PLA",
    },

    # =========================================================================
    # Fiberlogy PLA/pla
    # =========================================================================
    {
        "manufacturer": "fiberlogy",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "easy_",
        "name_prefix": ["Easy  ", "Easy "],
        "target_subtype": "easy_pla",
        "target_display_name": "Easy PLA",
    },
    {
        "manufacturer": "fiberlogy",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "impact_",
        "name_prefix": ["Impact  ", "Impact "],
        "target_subtype": "impact_pla",
        "target_display_name": "Impact PLA",
    },
    {
        "manufacturer": "fiberlogy",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "fibersatin_",
        "name_prefix": ["FiberSatin "],
        "target_subtype": "fibersatin_pla",
        "target_display_name": "FiberSatin PLA",
    },
    {
        "manufacturer": "fiberlogy",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "fiberwood_",
        "name_prefix": ["FiberWood "],
        "target_subtype": "fiberwood_pla",
        "target_display_name": "FiberWood PLA",
    },
    {
        "manufacturer": "fiberlogy",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "mineral_",
        "name_prefix": ["Mineral "],
        "target_subtype": "mineral_pla",
        "target_display_name": "Mineral PLA",
    },

    # =========================================================================
    # Fiberlogy PETG/petg
    # =========================================================================
    {
        "manufacturer": "fiberlogy",
        "material": "PETG",
        "source_subtype": "petg",
        "id_prefix": "easy_pet_g_",
        "name_prefix": ["Easy PET-G "],
        "target_subtype": "easy_petg",
        "target_display_name": "Easy PETG",
    },
    {
        "manufacturer": "fiberlogy",
        "material": "PETG",
        "source_subtype": "petg",
        "id_prefix": "pet_g_v0_",
        "name_prefix": ["PET-G V0 "],
        "target_subtype": "pet_g_v0_petg",
        "target_display_name": "PET-G V0 PETG",
    },

    # =========================================================================
    # Fiberlogy TPU/tpu
    # =========================================================================
    {
        "manufacturer": "fiberlogy",
        "material": "TPU",
        "source_subtype": "tpu",
        "id_prefix": "fiberflex_40d_",
        "name_prefix": ["FiberFlex 40D "],
        "target_subtype": "fiberflex_40d_tpu",
        "target_display_name": "FiberFlex 40D TPU",
    },
    {
        "manufacturer": "fiberlogy",
        "material": "TPU",
        "source_subtype": "tpu",
        "id_prefix": "fiberflex_30d_",
        "name_prefix": ["FiberFlex 30D "],
        "target_subtype": "fiberflex_30d_tpu",
        "target_display_name": "FiberFlex 30D TPU",
    },

    # =========================================================================
    # 3DPower PLA/pla
    # =========================================================================
    {
        "manufacturer": "3dpower",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "hyper_speed_",
        "name_prefix": ["Hyper Speed  ", "Hyper Speed "],
        "target_subtype": "hyper_speed_pla",
        "target_display_name": "Hyper Speed PLA",
    },
    {
        "manufacturer": "3dpower",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "ht_150_",
        "name_prefix": ["HT 150 "],
        "target_subtype": "ht_150_pla",
        "target_display_name": "HT 150 PLA",
    },
    {
        "manufacturer": "3dpower",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "basic_",
        "name_prefix": ["Basic  ", "Basic "],
        "target_subtype": "basic_pla",
        "target_display_name": "Basic PLA",
    },
    {
        "manufacturer": "3dpower",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "select_",
        "name_prefix": ["Select  ", "Select "],
        "target_subtype": "select_pla",
        "target_display_name": "Select PLA",
    },
    {
        "manufacturer": "3dpower",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "pastel_",
        "name_prefix": ["Pastel "],
        "target_subtype": "pastel_pla",
        "target_display_name": "Pastel PLA",
    },
    {
        "manufacturer": "3dpower",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "marble_",
        "name_prefix": ["Marble "],
        "target_subtype": "marble_pla",
        "target_display_name": "Marble PLA",
    },

    # =========================================================================
    # 3DPower PETG/petg
    # =========================================================================
    {
        "manufacturer": "3dpower",
        "material": "PETG",
        "source_subtype": "petg",
        "id_prefix": "basic_pet_g_",
        "name_prefix": ["Basic PET-G "],
        "target_subtype": "basic_petg",
        "target_display_name": "Basic PETG",
    },
    {
        "manufacturer": "3dpower",
        "material": "PETG",
        "source_subtype": "petg",
        "id_prefix": "hyper_speed_pet_g_",
        "name_prefix": ["Hyper Speed PET-G "],
        "target_subtype": "hyper_speed_petg",
        "target_display_name": "Hyper Speed PETG",
    },
    {
        "manufacturer": "3dpower",
        "material": "PETG",
        "source_subtype": "petg",
        "id_prefix": "select_",
        "name_prefix": ["Select  ", "Select "],
        "target_subtype": "select_petg",
        "target_display_name": "Select PETG",
    },

    # =========================================================================
    # 3DPower PA6/pa6
    # =========================================================================
    {
        "manufacturer": "3dpower",
        "material": "PA6",
        "source_subtype": "pa6",
        "id_prefix": "hyper_",
        "name_prefix": ["Hyper  ", "Hyper "],
        "target_subtype": "hyper_pa6",
        "target_display_name": "Hyper PA6",
    },

    # =========================================================================
    # Spectrum PETG/petg
    # =========================================================================
    {
        "manufacturer": "spectrum",
        "material": "PETG",
        "source_subtype": "petg",
        "id_prefix": "pet_g_premium_",
        "name_prefix": ["PET-G Premium "],
        "target_subtype": "pet_g_premium_petg",
        "target_display_name": "PET-G Premium PETG",
    },
    {
        "manufacturer": "spectrum",
        "material": "PETG",
        "source_subtype": "petg",
        "id_prefix": "the_filament_",
        "name_prefix": ["The Filament  ", "The Filament "],
        "target_subtype": "the_filament_petg",
        "target_display_name": "The Filament PETG",
    },
    {
        "manufacturer": "spectrum",
        "material": "PETG",
        "source_subtype": "petg",
        "id_prefix": "pet_g_ht100_",
        "name_prefix": ["PET-G HT100\u2122 ", "PET-G HT100 "],
        "target_subtype": "pet_g_ht100_petg",
        "target_display_name": "PET-G HT100 PETG",
    },
    {
        "manufacturer": "spectrum",
        "material": "PETG",
        "source_subtype": "petg",
        "id_prefix": "pet_g_glitter_",
        "name_prefix": ["PET-G Glitter "],
        "target_subtype": "pet_g_glitter_petg",
        "target_display_name": "PET-G Glitter PETG",
    },
    {
        "manufacturer": "spectrum",
        "material": "PETG",
        "source_subtype": "petg",
        "id_prefix": "pet_g_fr_v0_",
        "name_prefix": ["PET-G FR V0 "],
        "target_subtype": "pet_g_fr_v0_petg",
        "target_display_name": "PET-G FR V0 PETG",
    },
    {
        "manufacturer": "spectrum",
        "material": "PETG",
        "source_subtype": "petg",
        "id_prefix": "r_",
        "name_prefix": ["r "],
        "target_subtype": "r_petg",
        "target_display_name": "R PETG",
    },

    # =========================================================================
    # Spectrum PLA/silk_pla
    # =========================================================================
    {
        "manufacturer": "spectrum",
        "material": "PLA",
        "source_subtype": "silk_pla",
        "id_prefix": "huracan_",
        "name_prefix": ["Huracan  ", "Huracan "],
        "target_subtype": "huracan_silk_pla",
        "target_display_name": "Huracan Silk PLA",
    },
    {
        "manufacturer": "spectrum",
        "material": "PLA",
        "source_subtype": "silk_pla",
        "id_prefix": "flameguard_",
        "name_prefix": ["FlameGuard  ", "FlameGuard "],
        "target_subtype": "flameguard_silk_pla",
        "target_display_name": "FlameGuard Silk PLA",
    },
    {
        "manufacturer": "spectrum",
        "material": "PLA",
        "source_subtype": "silk_pla",
        "id_prefix": "glitter_",
        "name_prefix": ["Glitter "],
        "target_subtype": "glitter_silk_pla",
        "target_display_name": "Glitter Silk PLA",
    },
    {
        "manufacturer": "spectrum",
        "material": "PLA",
        "source_subtype": "silk_pla",
        "id_prefix": "crystal_",
        "name_prefix": ["Crystal "],
        "target_subtype": "crystal_silk_pla",
        "target_display_name": "Crystal Silk PLA",
    },
    {
        "manufacturer": "spectrum",
        "material": "PLA",
        "source_subtype": "silk_pla",
        "id_prefix": "metal_",
        "name_prefix": ["Metal "],
        "target_subtype": "metal_silk_pla",
        "target_display_name": "Metal Silk PLA",
    },

    # =========================================================================
    # Add:North PLA/pla
    # =========================================================================
    {
        "manufacturer": "add_north",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "e_",
        "name_prefix": ["E- "],
        "target_subtype": "e_pla",
        "target_display_name": "E PLA",
    },
    {
        "manufacturer": "add_north",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "x_",
        "name_prefix": ["X- "],
        "target_subtype": "x_pla",
        "target_display_name": "X PLA",
    },
    {
        "manufacturer": "add_north",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "economy_",
        "name_prefix": ["Economy "],
        "target_subtype": "economy_pla",
        "target_display_name": "Economy PLA",
    },
    {
        "manufacturer": "add_north",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "wood_",
        "name_prefix": ["Wood "],
        "target_subtype": "wood_pla",
        "target_display_name": "Wood PLA",
    },

    # =========================================================================
    # Recreus TPU/filaflex_tpu
    # NOTE: Longer prefixes first
    # =========================================================================
    {
        "manufacturer": "recreus",
        "material": "TPU",
        "source_subtype": "filaflex_tpu",
        "id_prefix": "95a_medium_flex_",
        "name_prefix": ["95A Medium Flex "],
        "target_subtype": "filaflex_95a_medium_flex",
        "target_display_name": "FilaFlex 95A Medium Flex",
    },
    {
        "manufacturer": "recreus",
        "material": "TPU",
        "source_subtype": "filaflex_tpu",
        "id_prefix": "70a_ultra_soft_",
        "name_prefix": ["70A Ultra Soft "],
        "target_subtype": "filaflex_70a_ultra_soft",
        "target_display_name": "FilaFlex 70A Ultra Soft",
    },
    {
        "manufacturer": "recreus",
        "material": "TPU",
        "source_subtype": "filaflex_tpu",
        "id_prefix": "95_foamy_",
        "name_prefix": ["95 Foamy "],
        "target_subtype": "filaflex_95_foamy",
        "target_display_name": "FilaFlex 95 Foamy",
    },
    {
        "manufacturer": "recreus",
        "material": "TPU",
        "source_subtype": "filaflex_tpu",
        "id_prefix": "82a_",
        "name_prefix": ["82A "],
        "target_subtype": "filaflex_82a",
        "target_display_name": "FilaFlex 82A",
    },
    {
        "manufacturer": "recreus",
        "material": "TPU",
        "source_subtype": "filaflex_tpu",
        "id_prefix": "60a_",
        "name_prefix": ["60A "],
        "target_subtype": "filaflex_60a",
        "target_display_name": "FilaFlex 60A",
    },

    # =========================================================================
    # 3DXTech PLA/pla
    # =========================================================================
    {
        "manufacturer": "3dxtech",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "economy_",
        "name_prefix": ["Economy  - ", "Economy  ", "Economy "],
        "target_subtype": "economy_pla",
        "target_display_name": "Economy PLA",
    },
    {
        "manufacturer": "3dxtech",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "ecomax_",
        "name_prefix": ["ECOMAX   ", "ECOMAX  ", "ECOMAX ", "Ecomax "],
        "target_subtype": "ecomax_pla",
        "target_display_name": "EcoMax PLA",
    },

    # =========================================================================
    # Sakata 3D PLA/pla
    # =========================================================================
    {
        "manufacturer": "sakata_3d",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "goprint_",
        "name_prefix": ["Go&Print "],
        "target_subtype": "goprint_pla",
        "target_display_name": "Go&Print PLA",
    },
    {
        "manufacturer": "sakata_3d",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "hr_870_",
        "name_prefix": ["HR-870 "],
        "target_subtype": "hr_870_pla",
        "target_display_name": "HR-870 PLA",
    },
    {
        "manufacturer": "sakata_3d",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "wood_",
        "name_prefix": ["Wood "],
        "target_subtype": "wood_pla",
        "target_display_name": "Wood PLA",
    },

    # =========================================================================
    # Econofil PLA/pla
    # =========================================================================
    {
        "manufacturer": "econofil",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "standard_",
        "name_prefix": ["Standard  ", "Standard "],
        "target_subtype": "standard_pla",
        "target_display_name": "Standard PLA",
    },

    # =========================================================================
    # ColorFabb PLA/pla
    # =========================================================================
    {
        "manufacturer": "colorfabb",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "r_semi_",
        "name_prefix": ["r-Semi--", "r-Semi-", "r-Semi "],
        "target_subtype": "r_semi_pla",
        "target_display_name": "r-Semi PLA",
    },
    {
        "manufacturer": "colorfabb",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "pha_",
        "name_prefix": ["/PHA ", "PHA "],
        "target_subtype": "pha_pla",
        "target_display_name": "PHA PLA",
    },
    {
        "manufacturer": "colorfabb",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "economy_",
        "name_prefix": ["Economy "],
        "target_subtype": "economy_pla",
        "target_display_name": "Economy PLA",
    },
    {
        "manufacturer": "colorfabb",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "lw_ht_",
        "name_prefix": ["LW--HT ", "LW-HT "],
        "target_subtype": "lw_ht_pla",
        "target_display_name": "LW-HT PLA",
    },
    {
        "manufacturer": "colorfabb",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "stonefill_",
        "name_prefix": ["stoneFill ", "StoneFill ", "Stonefill "],
        "target_subtype": "stonefill_pla",
        "target_display_name": "StoneFill PLA",
    },
    {
        "manufacturer": "colorfabb",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "semi_",
        "name_prefix": ["Semi- ", "Semi "],
        "target_subtype": "semi_pla",
        "target_display_name": "Semi PLA",
    },

    # =========================================================================
    # NoBuFil ABS/abs
    # =========================================================================
    {
        "manufacturer": "nobufil",
        "material": "ABS",
        "source_subtype": "abs",
        "id_prefix": "x_industrial_",
        "name_prefix": ["x Industrial "],
        "target_subtype": "x_industrial_abs",
        "target_display_name": "X Industrial ABS",
    },
    {
        "manufacturer": "nobufil",
        "material": "ABS",
        "source_subtype": "abs",
        "id_prefix": "x_astro_",
        "name_prefix": ["x Astro "],
        "target_subtype": "x_astro_abs",
        "target_display_name": "X Astro ABS",
    },
    {
        "manufacturer": "nobufil",
        "material": "ABS",
        "source_subtype": "abs",
        "id_prefix": "x_candy_",
        "name_prefix": ["x Candy "],
        "target_subtype": "x_candy_abs",
        "target_display_name": "X Candy ABS",
    },
    {
        "manufacturer": "nobufil",
        "material": "ABS",
        "source_subtype": "abs",
        "id_prefix": "x_neon_",
        "name_prefix": ["x Neon "],
        "target_subtype": "x_neon_abs",
        "target_display_name": "X Neon ABS",
    },

    # =========================================================================
    # NinjaTek TPU/tpu
    # NOTE: tpe_ prefix must come before ninjatek_ prefix
    # =========================================================================
    {
        "manufacturer": "ninjatek",
        "material": "TPU",
        "source_subtype": "tpu",
        "id_prefix": "tpe_ninjatek_edge_",
        "name_prefix": ["TPE NinjaTek Edge - ", "TPE NinjaTek Edge "],
        "target_subtype": "edge_tpu",
        "target_display_name": "Edge TPU",
    },
    {
        "manufacturer": "ninjatek",
        "material": "TPU",
        "source_subtype": "tpu",
        "id_prefix": "ninjatek_ninjaflex_",
        "name_prefix": ["NinjaTek NinjaFlex - ", "NinjaTek NinjaFlex "],
        "target_subtype": "ninjaflex_tpu",
        "target_display_name": "NinjaFlex TPU",
    },
    {
        "manufacturer": "ninjatek",
        "material": "TPU",
        "source_subtype": "tpu",
        "id_prefix": "ninjatek_cheetah_",
        "name_prefix": ["NinjaTek Cheetah - ", "NinjaTek Cheetah "],
        "target_subtype": "cheetah_tpu",
        "target_display_name": "Cheetah TPU",
    },
    {
        "manufacturer": "ninjatek",
        "material": "TPU",
        "source_subtype": "tpu",
        "id_prefix": "ninjatek_chinchilla_",
        "name_prefix": ["NinjaTek Chinchilla - ", "NinjaTek Chinchilla "],
        "target_subtype": "chinchilla_tpu",
        "target_display_name": "Chinchilla TPU",
    },

    # =========================================================================
    # Eolas Prints TPU/tpu
    # NOTE: Longer prefixes first
    # =========================================================================
    {
        "manufacturer": "eolas_prints",
        "material": "TPU",
        "source_subtype": "tpu",
        "id_prefix": "flex_d60_uv_resistant_",
        "name_prefix": ["Flex D60 UV Resistant "],
        "target_subtype": "flex_d60_uv_resistant_tpu",
        "target_display_name": "Flex D60 UV Resistant TPU",
    },
    {
        "manufacturer": "eolas_prints",
        "material": "TPU",
        "source_subtype": "tpu",
        "id_prefix": "flex_93a_",
        "name_prefix": ["Flex 93A "],
        "target_subtype": "flex_93a_tpu",
        "target_display_name": "Flex 93A TPU",
    },
    {
        "manufacturer": "eolas_prints",
        "material": "TPU",
        "source_subtype": "tpu",
        "id_prefix": "flex_d53_",
        "name_prefix": ["Flex D53 "],
        "target_subtype": "flex_d53_tpu",
        "target_display_name": "Flex D53 TPU",
    },

    # =========================================================================
    # eSUN PLA/pla
    # =========================================================================
    {
        "manufacturer": "esun",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "lithophane_cmyk_",
        "name_prefix": ["Lithophane + CMYK ", "Lithophane CMYK "],
        "target_subtype": "lithophane_cmyk_pla",
        "target_display_name": "Lithophane CMYK PLA",
    },
    {
        "manufacturer": "esun",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "chameleon_",
        "name_prefix": ["Chameleon  ", "Chameleon "],
        "target_subtype": "chameleon_pla",
        "target_display_name": "Chameleon PLA",
    },
    {
        "manufacturer": "esun",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "basic_",
        "name_prefix": ["Basic "],
        "target_subtype": "basic_pla",
        "target_display_name": "Basic PLA",
    },
    {
        "manufacturer": "esun",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "super_",
        "name_prefix": ["Super   ", "Super  ", "Super "],
        "target_subtype": "super_pla",
        "target_display_name": "Super PLA",
    },
    {
        "manufacturer": "esun",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "peak_",
        "name_prefix": ["Peak "],
        "target_subtype": "peak_pla",
        "target_display_name": "Peak PLA",
    },
    {
        "manufacturer": "esun",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "plus_",
        "name_prefix": ["Plus "],
        "target_subtype": "plus_pla",
        "target_display_name": "Plus PLA",
    },

    # =========================================================================
    # eSUN PLA/silk_pla
    # =========================================================================
    {
        "manufacturer": "esun",
        "material": "PLA",
        "source_subtype": "silk_pla",
        "id_prefix": "magic_",
        "name_prefix": ["Magic  ", "Magic "],
        "target_subtype": "magic_silk_pla",
        "target_display_name": "Magic Silk PLA",
    },
    {
        "manufacturer": "esun",
        "material": "PLA",
        "source_subtype": "silk_pla",
        "id_prefix": "mystic_",
        "name_prefix": ["Mystic  ", "Mystic "],
        "target_subtype": "mystic_silk_pla",
        "target_display_name": "Mystic Silk PLA",
    },
    {
        "manufacturer": "esun",
        "material": "PLA",
        "source_subtype": "silk_pla",
        "id_prefix": "rainbow_",
        "name_prefix": ["Rainbow  ", "Rainbow "],
        "target_subtype": "rainbow_silk_pla",
        "target_display_name": "Rainbow Silk PLA",
    },
    {
        "manufacturer": "esun",
        "material": "PLA",
        "source_subtype": "silk_pla",
        "id_prefix": "metal_",
        "name_prefix": ["Metal  ", "Metal "],
        "target_subtype": "metal_silk_pla",
        "target_display_name": "Metal Silk PLA",
    },
    {
        "manufacturer": "esun",
        "material": "PLA",
        "source_subtype": "silk_pla",
        "id_prefix": "candy_",
        "name_prefix": ["Candy  ", "Candy "],
        "target_subtype": "candy_silk_pla",
        "target_display_name": "Candy Silk PLA",
    },

    # =========================================================================
    # Print With Smile PETG/petg
    # =========================================================================
    {
        "manufacturer": "print_with_smile",
        "material": "PETG",
        "source_subtype": "petg",
        "id_prefix": "bicolor_metallic_pet_g_",
        "name_prefix": ["BICOLOR METALLIC PET-G "],
        "target_subtype": "bicolor_metallic_petg",
        "target_display_name": "Bicolor Metallic PETG",
    },
    {
        "manufacturer": "print_with_smile",
        "material": "PETG",
        "source_subtype": "petg",
        "id_prefix": "re_",
        "name_prefix": ["RE- "],
        "target_subtype": "re_petg",
        "target_display_name": "RE PETG",
    },

    # =========================================================================
    # Rosa3D PLA/pla
    # NOTE: Longer prefixes first
    # =========================================================================
    {
        "manufacturer": "rosa3d_filaments",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "plus_prospeedimpact_",
        "name_prefix": ["Plus ProSpeed(Impact) "],
        "target_subtype": "plus_prospeedimpact_pla",
        "target_display_name": "Plus ProSpeed Impact PLA",
    },
    {
        "manufacturer": "rosa3d_filaments",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "lw_aero_",
        "name_prefix": ["LW AERO "],
        "target_subtype": "lw_aero_pla",
        "target_display_name": "LW AERO PLA",
    },
    {
        "manufacturer": "rosa3d_filaments",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "galaxy_",
        "name_prefix": ["Galaxy "],
        "target_subtype": "galaxy_pla",
        "target_display_name": "Galaxy PLA",
    },
    {
        "manufacturer": "rosa3d_filaments",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "pastel_",
        "name_prefix": ["Pastel "],
        "target_subtype": "pastel_pla",
        "target_display_name": "Pastel PLA",
    },
    {
        "manufacturer": "rosa3d_filaments",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "starter_",
        "name_prefix": ["Starter "],
        "target_subtype": "starter_pla",
        "target_display_name": "Starter PLA",
    },
    {
        "manufacturer": "rosa3d_filaments",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "magic_",
        "name_prefix": ["Magic "],
        "target_subtype": "magic_pla",
        "target_display_name": "Magic PLA",
    },
    {
        "manufacturer": "rosa3d_filaments",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "refill_",
        "name_prefix": ["ReFill  ", "ReFill ", "Refill "],
        "target_subtype": "refill_pla",
        "target_display_name": "ReFill PLA",
    },

    # =========================================================================
    # Rosa3D PLA/silk_pla
    # =========================================================================
    {
        "manufacturer": "rosa3d_filaments",
        "material": "PLA",
        "source_subtype": "silk_pla",
        "id_prefix": "magic_",
        "name_prefix": ["Magic  ", "Magic "],
        "target_subtype": "magic_silk_pla",
        "target_display_name": "Magic Silk PLA",
    },
    {
        "manufacturer": "rosa3d_filaments",
        "material": "PLA",
        "source_subtype": "silk_pla",
        "id_prefix": "multicolour_",
        "name_prefix": ["Multicolour  ", "Multicolour "],
        "target_subtype": "multicolour_silk_pla",
        "target_display_name": "Multicolour Silk PLA",
    },
    {
        "manufacturer": "rosa3d_filaments",
        "material": "PLA",
        "source_subtype": "silk_pla",
        "id_prefix": "rainbow_",
        "name_prefix": ["Rainbow  ", "Rainbow "],
        "target_subtype": "rainbow_silk_pla",
        "target_display_name": "Rainbow Silk PLA",
    },
    {
        "manufacturer": "rosa3d_filaments",
        "material": "PLA",
        "source_subtype": "silk_pla",
        "id_prefix": "refill_",
        "name_prefix": ["ReFill  ", "ReFill ", "Refill "],
        "target_subtype": "refill_silk_pla",
        "target_display_name": "ReFill Silk PLA",
    },

    # =========================================================================
    # Polymaker PLA/panchroma_pla
    # =========================================================================
    {
        "manufacturer": "polymaker",
        "material": "PLA",
        "source_subtype": "panchroma_pla",
        "id_prefix": "starlight_",
        "name_prefix": ["Starlight "],
        "target_subtype": "starlight_panchroma_pla",
        "target_display_name": "Starlight Panchroma PLA",
    },
    {
        "manufacturer": "polymaker",
        "material": "PLA",
        "source_subtype": "panchroma_pla",
        "id_prefix": "satin_",
        "name_prefix": ["Satin "],
        "target_subtype": "satin_panchroma_pla",
        "target_display_name": "Satin Panchroma PLA",
    },
    {
        "manufacturer": "polymaker",
        "material": "PLA",
        "source_subtype": "panchroma_pla",
        "id_prefix": "neon_",
        "name_prefix": ["Neon "],
        "target_subtype": "neon_panchroma_pla",
        "target_display_name": "Neon Panchroma PLA",
    },
    {
        "manufacturer": "polymaker",
        "material": "PLA",
        "source_subtype": "panchroma_pla",
        "id_prefix": "translucent_",
        "name_prefix": ["Translucent "],
        "target_subtype": "translucent_panchroma_pla",
        "target_display_name": "Translucent Panchroma PLA",
    },
    {
        "manufacturer": "polymaker",
        "material": "PLA",
        "source_subtype": "panchroma_pla",
        "id_prefix": "marble_",
        "name_prefix": ["Marble "],
        "target_subtype": "marble_panchroma_pla",
        "target_display_name": "Marble Panchroma PLA",
    },
    {
        "manufacturer": "polymaker",
        "material": "PLA",
        "source_subtype": "panchroma_pla",
        "id_prefix": "galaxy_",
        "name_prefix": ["Galaxy "],
        "target_subtype": "galaxy_panchroma_pla",
        "target_display_name": "Galaxy Panchroma PLA",
    },
    {
        "manufacturer": "polymaker",
        "material": "PLA",
        "source_subtype": "panchroma_pla",
        "id_prefix": "celestial_",
        "name_prefix": ["Celestial "],
        "target_subtype": "celestial_panchroma_pla",
        "target_display_name": "Celestial Panchroma PLA",
    },
    {
        "manufacturer": "polymaker",
        "material": "PLA",
        "source_subtype": "panchroma_pla",
        "id_prefix": "metallic_",
        "name_prefix": ["Metallic "],
        "target_subtype": "metallic_panchroma_pla",
        "target_display_name": "Metallic Panchroma PLA",
    },
    {
        "manufacturer": "polymaker",
        "material": "PLA",
        "source_subtype": "panchroma_pla",
        "id_prefix": "temp_shift_",
        "name_prefix": ["Temp Shift "],
        "target_subtype": "temp_shift_panchroma_pla",
        "target_display_name": "Temp Shift Panchroma PLA",
    },
    {
        "manufacturer": "polymaker",
        "material": "PLA",
        "source_subtype": "panchroma_pla",
        "id_prefix": "gradient_",
        "name_prefix": ["Gradient "],
        "target_subtype": "gradient_panchroma_pla",
        "target_display_name": "Gradient Panchroma PLA",
    },

    # =========================================================================
    # Polymaker PLA/panchroma_matte_pla
    # =========================================================================
    {
        "manufacturer": "polymaker",
        "material": "PLA",
        "source_subtype": "panchroma_matte_pla",
        "id_prefix": "pastel_",
        "name_prefix": ["Pastel "],
        "target_subtype": "pastel_panchroma_matte_pla",
        "target_display_name": "Pastel Panchroma Matte PLA",
    },
    {
        "manufacturer": "polymaker",
        "material": "PLA",
        "source_subtype": "panchroma_matte_pla",
        "id_prefix": "gradient_",
        "name_prefix": ["Gradient "],
        "target_subtype": "gradient_panchroma_matte_pla",
        "target_display_name": "Gradient Panchroma Matte PLA",
    },
    {
        "manufacturer": "polymaker",
        "material": "PLA",
        "source_subtype": "panchroma_matte_pla",
        "id_prefix": "army_",
        "name_prefix": ["Army "],
        "target_subtype": "army_panchroma_matte_pla",
        "target_display_name": "Army Panchroma Matte PLA",
    },
    {
        "manufacturer": "polymaker",
        "material": "PLA",
        "source_subtype": "panchroma_matte_pla",
        "id_prefix": "dual_",
        "name_prefix": ["Dual "],
        "target_subtype": "dual_panchroma_matte_pla",
        "target_display_name": "Dual Panchroma Matte PLA",
    },
    {
        "manufacturer": "polymaker",
        "material": "PLA",
        "source_subtype": "panchroma_matte_pla",
        "id_prefix": "muted_",
        "name_prefix": ["Muted "],
        "target_subtype": "muted_panchroma_matte_pla",
        "target_display_name": "Muted Panchroma Matte PLA",
    },

    # =========================================================================
    # Polymaker PLA/polylite_pla
    # =========================================================================
    {
        "manufacturer": "polymaker",
        "material": "PLA",
        "source_subtype": "polylite_pla",
        "id_prefix": "metallic_",
        "name_prefix": ["Metallic "],
        "target_subtype": "metallic_polylite_pla",
        "target_display_name": "Metallic PolyLite PLA",
    },
    {
        "manufacturer": "polymaker",
        "material": "PLA",
        "source_subtype": "polylite_pla",
        "id_prefix": "lw_",
        "name_prefix": ["Lw "],
        "target_subtype": "lw_polylite_pla",
        "target_display_name": "LW PolyLite PLA",
    },

    # =========================================================================
    # PrimaCreator PLA/primaselect_pla
    # NOTE: Longer prefixes first
    # =========================================================================
    {
        "manufacturer": "primacreator",
        "material": "PLA",
        "source_subtype": "primaselect_pla",
        "id_prefix": "metal_shine_",
        "name_prefix": ["Metal Shine "],
        "target_subtype": "metal_shine_primaselect_pla",
        "target_display_name": "Metal Shine PrimaSelect PLA",
    },
    {
        "manufacturer": "primacreator",
        "material": "PLA",
        "source_subtype": "primaselect_pla",
        "id_prefix": "flame_retardant_",
        "name_prefix": ["Flame Retardant "],
        "target_subtype": "flame_retardant_primaselect_pla",
        "target_display_name": "Flame Retardant PrimaSelect PLA",
    },
    {
        "manufacturer": "primacreator",
        "material": "PLA",
        "source_subtype": "primaselect_pla",
        "id_prefix": "satin_",
        "name_prefix": ["Satin "],
        "target_subtype": "satin_primaselect_pla",
        "target_display_name": "Satin PrimaSelect PLA",
    },
    {
        "manufacturer": "primacreator",
        "material": "PLA",
        "source_subtype": "primaselect_pla",
        "id_prefix": "pastel_",
        "name_prefix": ["Pastel "],
        "target_subtype": "pastel_primaselect_pla",
        "target_display_name": "Pastel PrimaSelect PLA",
    },
    {
        "manufacturer": "primacreator",
        "material": "PLA",
        "source_subtype": "primaselect_pla",
        "id_prefix": "sparkle_",
        "name_prefix": ["Sparkle "],
        "target_subtype": "sparkle_primaselect_pla",
        "target_display_name": "Sparkle PrimaSelect PLA",
    },
    {
        "manufacturer": "primacreator",
        "material": "PLA",
        "source_subtype": "primaselect_pla",
        "id_prefix": "marble_",
        "name_prefix": ["Marble "],
        "target_subtype": "marble_primaselect_pla",
        "target_display_name": "Marble PrimaSelect PLA",
    },
    {
        "manufacturer": "primacreator",
        "material": "PLA",
        "source_subtype": "primaselect_pla",
        "id_prefix": "gradient_",
        "name_prefix": ["Gradient "],
        "target_subtype": "gradient_primaselect_pla",
        "target_display_name": "Gradient PrimaSelect PLA",
    },

    # =========================================================================
    # Printed Solid PLA/silk_pla
    # NOTE: Longer prefixes first (tricolor_ before bicolor_, shiny_gradient_ before gradient_)
    # =========================================================================
    {
        "manufacturer": "printedsolid",
        "material": "PLA",
        "source_subtype": "silk_pla",
        "id_prefix": "tricolor_magic_",
        "name_prefix": ["TriColor  Magic-", "TriColor Magic-", "Tricolor  Magic-", "Tricolor Magic-"],
        "target_subtype": "tricolor_magic_silk_pla",
        "target_display_name": "TriColor Magic Silk PLA",
    },
    {
        "manufacturer": "printedsolid",
        "material": "PLA",
        "source_subtype": "silk_pla",
        "id_prefix": "bicolor_magic_",
        "name_prefix": ["Bicolor  Magic-", "Bicolor  Magic ", "Bicolor Magic-", "Bicolor Magic "],
        "target_subtype": "bicolor_magic_silk_pla",
        "target_display_name": "Bicolor Magic Silk PLA",
    },
    {
        "manufacturer": "printedsolid",
        "material": "PLA",
        "source_subtype": "silk_pla",
        "id_prefix": "shiny_gradient_",
        "name_prefix": ["Shiny Gradient-", "Shiny Gradient "],
        "target_subtype": "shiny_gradient_silk_pla",
        "target_display_name": "Shiny Gradient Silk PLA",
    },
    {
        "manufacturer": "printedsolid",
        "material": "PLA",
        "source_subtype": "silk_pla",
        "id_prefix": "rainbow_",
        "name_prefix": ["Rainbow-", "Rainbow "],
        "target_subtype": "rainbow_silk_pla",
        "target_display_name": "Rainbow Silk PLA",
    },
    {
        "manufacturer": "printedsolid",
        "material": "PLA",
        "source_subtype": "silk_pla",
        "id_prefix": "gradient_",
        "name_prefix": ["Gradient-", "Gradient "],
        "target_subtype": "gradient_silk_pla",
        "target_display_name": "Gradient Silk PLA",
    },

    # =========================================================================
    # Hatchbox PLA/pla (only actual product lines, not color descriptors)
    # =========================================================================
    {
        "manufacturer": "hatchbox",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "metallic_finish_",
        "name_prefix": ["Metallic Finish "],
        "target_subtype": "metallic_finish_pla",
        "target_display_name": "Metallic Finish PLA",
    },
    {
        "manufacturer": "hatchbox",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "uv_color_changing_",
        "name_prefix": ["UV Color Changing "],
        "target_subtype": "uv_color_changing_pla",
        "target_display_name": "UV Color Changing PLA",
    },
    {
        "manufacturer": "hatchbox",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "transparent_",
        "name_prefix": ["Transparent "],
        "target_subtype": "transparent_pla",
        "target_display_name": "Transparent PLA",
    },
    {
        "manufacturer": "hatchbox",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "wood_",
        "name_prefix": ["Wood "],
        "target_subtype": "wood_pla",
        "target_display_name": "Wood PLA",
    },

    # =========================================================================
    # Filamentree PLA/pla
    # =========================================================================
    {
        "manufacturer": "filamentree",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "plus_",
        "name_prefix": ["Plus "],
        "target_subtype": "plus_pla",
        "target_display_name": "Plus PLA",
    },
    {
        "manufacturer": "filamentree",
        "material": "PLA",
        "source_subtype": "pla",
        "id_prefix": "blaster_",
        "name_prefix": ["Blaster "],
        "target_subtype": "blaster_pla",
        "target_display_name": "Blaster PLA",
    },

    # =========================================================================
    # Devil Design PETG/petg (only galaxy is a clear product line)
    # =========================================================================
    {
        "manufacturer": "devil_design",
        "material": "PETG",
        "source_subtype": "petg",
        "id_prefix": "galaxy_",
        "name_prefix": ["Galaxy "],
        "target_subtype": "galaxy_petg",
        "target_display_name": "Galaxy PETG",
    },
]


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def clean_stripped_name(stripped: str) -> str:
    """Clean up a stripped name: remove surrounding quotes, leading dashes, normalize."""
    stripped = stripped.strip()
    # Strip surrounding quotes (filamentpm uses "Color Name" format)
    if stripped.startswith('"') and stripped.endswith('"') and len(stripped) > 2:
        stripped = stripped[1:-1].strip()
    elif stripped.startswith('"'):
        stripped = stripped[1:].strip()
    # Strip leading dashes
    stripped = stripped.lstrip('-').strip()
    if stripped:
        return stripped[0].upper() + stripped[1:]
    return ""


def strip_name_prefix(name: str, name_prefixes: list[str]) -> str:
    """Strip the product-line prefix from the display name.

    Tries each prefix in order (longest first for safety).
    """
    # Sort by length descending to match longest prefix first
    for prefix in sorted(name_prefixes, key=len, reverse=True):
        if name.startswith(prefix):
            result = clean_stripped_name(name[len(prefix):])
            if result:
                return result
            return name

    # Try case-insensitive match
    for prefix in sorted(name_prefixes, key=len, reverse=True):
        if name.lower().startswith(prefix.lower()):
            result = clean_stripped_name(name[len(prefix):])
            if result:
                return result
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

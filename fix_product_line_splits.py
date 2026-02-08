#!/usr/bin/env python3
"""One-time script to split product-line prefixes from variant names into
their own filament_type directories.

Handles cases where variant directories embed a product-line identifier
(e.g., ``850_black``, ``3dxmax_red``, ``a95_white``) that should instead
live at the filament_type level of the directory hierarchy.

Usage:
  python fix_product_line_splits.py              # dry-run, prints what would be done
  python fix_product_line_splits.py --apply      # apply fixes
"""

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Helpers (same as fix_manual_review.py)
# ---------------------------------------------------------------------------

UPPERCASE_WORDS = {
    "ht", "fme", "pmuc", "ral", "pei", "pla", "petg", "abs", "asa",
    "tpu", "tpe", "pekk", "ppe", "ppsu", "tpi", "cf", "mc", "sc",
    "uv", "fst1", "3d4000fl", "pa11", "pa6", "pa12", "gf", "cc",
    "esd", "emi", "pc", "fr", "v0",
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
# Product line splits: old_path (relative to data/) -> (new_filament_id, new_variant_id)
# ---------------------------------------------------------------------------

PRODUCT_LINE_SPLITS: dict[str, tuple[str, str]] = {
    # =======================================================================
    # sakata_3d — PLA 850 (39 variants)
    # =======================================================================
    "sakata_3d/PLA/pla/850_black": ("850", "black"),
    "sakata_3d/PLA/pla/850_blue": ("850", "blue"),
    "sakata_3d/PLA/pla/850_chocolate": ("850", "chocolate"),
    "sakata_3d/PLA/pla/850_clay": ("850", "clay"),
    "sakata_3d/PLA/pla/850_fluor_light_green": ("850", "fluor_light_green"),
    "sakata_3d/PLA/pla/850_fluor_lime": ("850", "fluor_lime"),
    "sakata_3d/PLA/pla/850_fluor_orange": ("850", "fluor_orange"),
    "sakata_3d/PLA/pla/850_fluor_orange_fresh": ("850", "fluor_orange_fresh"),
    "sakata_3d/PLA/pla/850_fluor_yellow": ("850", "fluor_yellow"),
    "sakata_3d/PLA/pla/850_fuchsia": ("850", "fuchsia"),
    "sakata_3d/PLA/pla/850_gold": ("850", "gold"),
    "sakata_3d/PLA/pla/850_granite": ("850", "granite"),
    "sakata_3d/PLA/pla/850_green": ("850", "green"),
    "sakata_3d/PLA/pla/850_grey": ("850", "grey"),
    "sakata_3d/PLA/pla/850_ivory": ("850", "ivory"),
    "sakata_3d/PLA/pla/850_magic_coal": ("850", "magic_coal"),
    "sakata_3d/PLA/pla/850_magic_navy_blue": ("850", "magic_navy_blue"),
    "sakata_3d/PLA/pla/850_magic_plus_blue": ("850", "magic_plus_blue"),
    "sakata_3d/PLA/pla/850_magic_plus_coal": ("850", "magic_plus_coal"),
    "sakata_3d/PLA/pla/850_magic_plus_red": ("850", "magic_plus_red"),
    "sakata_3d/PLA/pla/850_magic_plus_silver": ("850", "magic_plus_silver"),
    "sakata_3d/PLA/pla/850_magic_purple": ("850", "magic_purple"),
    "sakata_3d/PLA/pla/850_magic_silver": ("850", "magic_silver"),
    "sakata_3d/PLA/pla/850_magic_star_gold": ("850", "magic_star_gold"),
    "sakata_3d/PLA/pla/850_militar_tone_1_gc": ("850", "militar_tone_1_gc"),
    "sakata_3d/PLA/pla/850_militar_tone_2": ("850", "militar_tone_2"),
    "sakata_3d/PLA/pla/850_natural": ("850", "natural"),
    "sakata_3d/PLA/pla/850_orange": ("850", "orange"),
    "sakata_3d/PLA/pla/850_pink": ("850", "pink"),
    "sakata_3d/PLA/pla/850_purple": ("850", "purple"),
    "sakata_3d/PLA/pla/850_red": ("850", "red"),
    "sakata_3d/PLA/pla/850_silver": ("850", "silver"),
    "sakata_3d/PLA/pla/850_skin_tone_1": ("850", "skin_tone_1"),
    "sakata_3d/PLA/pla/850_skin_tone_2": ("850", "skin_tone_2"),
    "sakata_3d/PLA/pla/850_sky_blue": ("850", "sky_blue"),
    "sakata_3d/PLA/pla/850_solidary": ("850", "solidary"),
    "sakata_3d/PLA/pla/850_surf_green": ("850", "surf_green"),
    "sakata_3d/PLA/pla/850_white": ("850", "white"),
    "sakata_3d/PLA/pla/850_yellow": ("850", "yellow"),

    # sakata_3d — Silk PLA 850 (9 variants)
    "sakata_3d/PLA/silk_pla/850_arctic": ("silk_850", "arctic"),
    "sakata_3d/PLA/silk_pla/850_clover": ("silk_850", "clover"),
    "sakata_3d/PLA/silk_pla/850_fir_green": ("silk_850", "fir_green"),
    "sakata_3d/PLA/silk_pla/850_gold": ("silk_850", "gold"),
    "sakata_3d/PLA/silk_pla/850_midnight": ("silk_850", "midnight"),
    "sakata_3d/PLA/silk_pla/850_ocean": ("silk_850", "ocean"),
    "sakata_3d/PLA/silk_pla/850_snow": ("silk_850", "snow"),
    "sakata_3d/PLA/silk_pla/850_sunset": ("silk_850", "sunset"),
    "sakata_3d/PLA/silk_pla/850_wine": ("silk_850", "wine"),

    # sakata_3d — PLA 700 (3 variants)
    "sakata_3d/PLA/pla/700_black": ("700", "black"),
    "sakata_3d/PLA/pla/700_grey": ("700", "grey"),
    "sakata_3d/PLA/pla/700_white": ("700", "white"),

    # =======================================================================
    # 3dxtech — 3DXTech ABS (13 variants)
    # =======================================================================
    "3dxtech/ABS/abs/3dxtech_black": ("3dxtech", "black"),
    "3dxtech/ABS/abs/3dxtech_burgundy": ("3dxtech", "burgundy"),
    "3dxtech/ABS/abs/3dxtech_dark_grey": ("3dxtech", "dark_grey"),
    "3dxtech/ABS/abs/3dxtech_green": ("3dxtech", "green"),
    "3dxtech/ABS/abs/3dxtech_lightglacier_grey": ("3dxtech", "lightglacier_grey"),
    "3dxtech/ABS/abs/3dxtech_metallic_copper": ("3dxtech", "metallic_copper"),
    "3dxtech/ABS/abs/3dxtech_metallic_gold": ("3dxtech", "metallic_gold"),
    "3dxtech/ABS/abs/3dxtech_natural": ("3dxtech", "natural"),
    "3dxtech/ABS/abs/3dxtech_orange": ("3dxtech", "orange"),
    "3dxtech/ABS/abs/3dxtech_red": ("3dxtech", "red"),
    "3dxtech/ABS/abs/3dxtech_reflex_blue": ("3dxtech", "reflex_blue"),
    "3dxtech/ABS/abs/3dxtech_white": ("3dxtech", "white"),
    "3dxtech/ABS/abs/3dxtech_yellow": ("3dxtech", "yellow"),

    # 3dxtech — 3DXMax across materials (16 variants)
    "3dxtech/ABS/abs/3dxmax_pc_black": ("3dxmax", "pc_black"),
    "3dxtech/ASA/asa/3dxmax_black": ("3dxmax", "black"),
    "3dxtech/ASA/asa/3dxmax_dark_grey": ("3dxmax", "dark_grey"),
    "3dxtech/ASA/asa/3dxmax_flat_dark_earth": ("3dxmax", "flat_dark_earth"),
    "3dxtech/ASA/asa/3dxmax_green": ("3dxmax", "green"),
    "3dxtech/ASA/asa/3dxmax_natural": ("3dxmax", "natural"),
    "3dxtech/ASA/asa/3dxmax_orange": ("3dxmax", "orange"),
    "3dxtech/ASA/asa/3dxmax_red": ("3dxmax", "red"),
    "3dxtech/ASA/asa/3dxmax_reflex_blue": ("3dxmax", "reflex_blue"),
    "3dxtech/ASA/asa/3dxmax_white": ("3dxmax", "white"),
    "3dxtech/ASA/asa/3dxmax_yellow": ("3dxmax", "yellow"),
    "3dxtech/HIPS/hips/3dxmax_blue": ("3dxmax", "blue"),
    "3dxtech/HIPS/hips/3dxmax_natural": ("3dxmax", "natural"),
    "3dxtech/HIPS/hips/3dxmax_red": ("3dxmax", "red"),
    "3dxtech/PC/pc/3dxmax_black": ("3dxmax", "black"),
    "3dxtech/PC/pc/3dxmax_white": ("3dxmax", "white"),

    # 3dxtech — 3DXStat ESD (8 variants)
    "3dxtech/ABS/abs/3dxstat_esd_black": ("3dxstat_esd", "black"),
    "3dxtech/PA12/pa12/3dxstat_esd_nylon_12_black": ("3dxstat_esd", "nylon_12_black"),
    "3dxtech/PC/pc/3dxstat_esd_black": ("3dxstat_esd", "black"),
    "3dxtech/PEI/pei/3dxstat_esd_ultem_1010_black": ("3dxstat_esd", "ultem_1010_black"),
    "3dxtech/PEKK/pekk/3dxstat_esd_a_black": ("3dxstat_esd", "a_black"),
    "3dxtech/PETG/petg/3dxstat_esd_black": ("3dxstat_esd", "black"),
    "3dxtech/PLA/pla/3dxstat_esd_black": ("3dxstat_esd", "black"),
    "3dxtech/TPU/tpu/3dxstat_esd_flex_90a_black": ("3dxstat_esd", "flex_90a_black"),

    # 3dxtech — 3DXStat EMI (1 variant)
    "3dxtech/PETG/petg/3dxstat_emi_black": ("3dxstat_emi", "black"),

    # 3dxtech — 3DXFlex (3 variants)
    "3dxtech/TPU/tpu/3dxflex_85a_black": ("3dxflex", "85a_black"),
    "3dxtech/TPU/tpu/3dxflex_95a": ("3dxflex", "95a_black"),
    "3dxtech/TPU/gf_tpu/3dxflex_gf30_black": ("3dxflex_gf30", "black"),

    # spectrum and prusament entries moved to DUPLICATES_TO_DELETE
    # (target directories already exist with proper data)

    # =======================================================================
    # 3djake — TPU A95 (14 variants)
    # =======================================================================
    "3djake/TPU/tpu/a95_black": ("a95", "black"),
    "3djake/TPU/tpu/a95_dark_blue": ("a95", "dark_blue"),
    "3djake/TPU/tpu/a95_dark_green": ("a95", "dark_green"),
    "3djake/TPU/tpu/a95_dark_grey": ("a95", "dark_grey"),
    "3djake/TPU/tpu/a95_light_blue": ("a95", "light_blue"),
    "3djake/TPU/tpu/a95_light_green": ("a95", "light_green"),
    "3djake/TPU/tpu/a95_light_grey": ("a95", "light_grey"),
    "3djake/TPU/tpu/a95_orange": ("a95", "orange"),
    "3djake/TPU/tpu/a95_purple": ("a95", "purple"),
    "3djake/TPU/tpu/a95_red": ("a95", "red"),
    "3djake/TPU/tpu/a95_silver": ("a95", "silver"),
    "3djake/TPU/tpu/a95_transparent": ("a95", "transparent"),
    "3djake/TPU/tpu/a95_white": ("a95", "white"),
    "3djake/TPU/tpu/a95_yellow": ("a95", "yellow"),

    # =======================================================================
    # aurapol — PLA HT110 (9 variants)
    # =======================================================================
    "aurapol/PLA/pla/ht110_black": ("ht110", "black"),
    "aurapol/PLA/pla/ht110_blue": ("ht110", "blue"),
    "aurapol/PLA/pla/ht110_body_color": ("ht110", "body_color"),
    "aurapol/PLA/pla/ht110_brown": ("ht110", "brown"),
    "aurapol/PLA/pla/ht110_green": ("ht110", "green"),
    "aurapol/PLA/pla/ht110_machine_blue": ("ht110", "machine_blue"),
    "aurapol/PLA/pla/ht110_red": ("ht110", "red"),
    "aurapol/PLA/pla/ht110_white": ("ht110", "white"),
    "aurapol/PLA/pla/ht110_yellow": ("ht110", "yellow"),

    # =======================================================================
    # filamentpm — TPE 32 Rubberjet Flex (2 variants)
    # =======================================================================
    "filamentpm/TPE/tpe/32_rubberjet_flex_black": ("32_rubberjet_flex", "black"),
    "filamentpm/TPE/tpe/32_rubberjet_flex_natur": ("32_rubberjet_flex", "natur"),

    # filamentpm — TPE 88 Rubberjet Flex (4 variants)
    "filamentpm/TPE/tpe/88_rubberjet_flex_black": ("88_rubberjet_flex", "black"),
    "filamentpm/TPE/tpe/88_rubberjet_flex_blue": ("88_rubberjet_flex", "blue"),
    "filamentpm/TPE/tpe/88_rubberjet_flex_red": ("88_rubberjet_flex", "red"),
    "filamentpm/TPE/tpe/88_rubberjet_flex_translucent": ("88_rubberjet_flex", "translucent"),

    # filamentpm — TPU 96 (3 variants)
    "filamentpm/TPU/tpu/96_black": ("96", "black"),
    "filamentpm/TPU/tpu/96_natur": ("96", "natur"),
    "filamentpm/TPU/tpu/96_white": ("96", "white"),

    # =======================================================================
    # coex_3d — PLA VO3D High Impact (8 variants)
    # =======================================================================
    "coex_3d/PLA/pla/vo3d_high_impact_bright_white": ("vo3d_high_impact", "bright_white"),
    "coex_3d/PLA/pla/vo3d_high_impact_cobalt_blue": ("vo3d_high_impact", "cobalt_blue"),
    "coex_3d/PLA/pla/vo3d_high_impact_forest_green": ("vo3d_high_impact", "forest_green"),
    "coex_3d/PLA/pla/vo3d_high_impact_midnight_black": ("vo3d_high_impact", "midnight_black"),
    "coex_3d/PLA/pla/vo3d_high_impact_scarlet_red": ("vo3d_high_impact", "scarlet_red"),
    "coex_3d/PLA/pla/vo3d_high_impact_space_gray": ("vo3d_high_impact", "space_gray"),
    "coex_3d/PLA/pla/vo3d_high_impact_stone_gray": ("vo3d_high_impact", "stone_gray"),
    "coex_3d/PLA/pla/vo3d_high_impact_taxicab_yellow": ("vo3d_high_impact", "taxicab_yellow"),

    # =======================================================================
    # smart_materials_3d — PLA 3D850 (3 variants)
    # =======================================================================
    "smart_materials_3d/PLA/pla/3d850_ivory_white": ("3d850", "ivory_white"),
    "smart_materials_3d/PLA/pla/3d850_natural": ("3d850", "natural"),
    "smart_materials_3d/PLA/pla/3d850_true_black": ("3d850", "true_black"),

    # smart_materials_3d — PLA 3D870 (2 variants)
    "smart_materials_3d/PLA/pla/3d870": ("3d870", "natural"),
    "smart_materials_3d/PLA/pla/3d870_true_black": ("3d870", "true_black"),

    # =======================================================================
    # extrudr — PLA NX2 Matt (22 variants)
    # =======================================================================
    "extrudr/PLA/matte_pla/nx2_matt": ("nx2_matt", "yellow"),
    "extrudr/PLA/matte_pla/nx2_matt_anthracite_ral_7016": ("nx2_matt", "anthracite_ral_7016"),
    "extrudr/PLA/matte_pla/nx2_matt_black_ral_9017": ("nx2_matt", "black_ral_9017"),
    "extrudr/PLA/matte_pla/nx2_matt_blue_steel_ral_5013": ("nx2_matt", "blue_steel_ral_5013"),
    "extrudr/PLA/matte_pla/nx2_matt_emerald_green_ral_6001": ("nx2_matt", "emerald_green_ral_6001"),
    "extrudr/PLA/matte_pla/nx2_matt_epic_purple_ral_4007": ("nx2_matt", "epic_purple_ral_4007"),
    "extrudr/PLA/matte_pla/nx2_matt_grey_ral_7044": ("nx2_matt", "grey_ral_7044"),
    "extrudr/PLA/matte_pla/nx2_matt_hellfire_red_ral_3024": ("nx2_matt", "hellfire_red_ral_3024"),
    "extrudr/PLA/matte_pla/nx2_matt_light_blue_ral_5012": ("nx2_matt", "light_blue_ral_5012"),
    "extrudr/PLA/matte_pla/nx2_matt_metallic_grey_ral_9023": ("nx2_matt", "metallic_grey_ral_9023"),
    "extrudr/PLA/matte_pla/nx2_matt_military_beige_ral_1001": ("nx2_matt", "military_beige_ral_1001"),
    "extrudr/PLA/matte_pla/nx2_matt_military_green_ral_6003": ("nx2_matt", "military_green_ral_6003"),
    "extrudr/PLA/matte_pla/nx2_matt_navy_blue_ral_5003": ("nx2_matt", "navy_blue_ral_5003"),
    "extrudr/PLA/matte_pla/nx2_matt_neon_orange_ral_2005": ("nx2_matt", "neon_orange_ral_2005"),
    "extrudr/PLA/matte_pla/nx2_matt_orange_ral_2009": ("nx2_matt", "orange_ral_2009"),
    "extrudr/PLA/matte_pla/nx2_matt_purple_ral_4008": ("nx2_matt", "purple_ral_4008"),
    "extrudr/PLA/matte_pla/nx2_matt_signal_green_ral_6037": ("nx2_matt", "signal_green_ral_6037"),
    "extrudr/PLA/matte_pla/nx2_matt_silver_ral_9006": ("nx2_matt", "silver_ral_9006"),
    "extrudr/PLA/matte_pla/nx2_matt_turquoise_ral_5018": ("nx2_matt", "turquoise_ral_5018"),
    "extrudr/PLA/matte_pla/nx2_matt_white_ral_9003": ("nx2_matt", "white_ral_9003"),
    "extrudr/PLA/matte_pla/nx2_matt_yellow_ral_1023": ("nx2_matt", "yellow_ral_1023"),
    # This one is in pla/ instead of matte_pla/ but goes to the same target
    "extrudr/PLA/pla/nx2_matt_brown_ral_8007": ("nx2_matt", "brown_ral_8007"),

    # =======================================================================
    # winkle — PLA UL94 V0 (3 variants)
    # =======================================================================
    "winkle/PLA/pla/ul94_v0_black": ("ul94_v0", "black"),
    "winkle/PLA/pla/ul94_v0_grey": ("ul94_v0", "grey"),
    "winkle/PLA/pla/ul94_v0_white": ("ul94_v0", "white"),

    # prusament entries moved to DUPLICATES_TO_DELETE

    # =======================================================================
    # rosa3d_filaments — ABS V0 FR (2 variants)
    # =======================================================================
    "rosa3d_filaments/ABS/abs/v0_fr_black": ("v0_fr", "black"),
    "rosa3d_filaments/ABS/abs/v0_fr_white": ("v0_fr", "white"),

    # rosa3d_filaments — ASA 5Kevlar (2 variants)
    "rosa3d_filaments/ASA/asa/5kevlar_black": ("5kevlar", "black"),
    "rosa3d_filaments/ASA/asa/5kevlar_natural": ("5kevlar", "natural"),

    # rosa3d_filaments — PVA 2 (1 variant)
    "rosa3d_filaments/PVA/pva/2_natural": ("2", "natural"),

    # =======================================================================
    # das_filament — TPU V2 Flexibel (3 variants)
    # =======================================================================
    "das_filament/TPU/tpu/v2_flexibel_natur": ("v2_flexibel", "natur"),
    "das_filament/TPU/tpu/v2_flexibel_schwarz": ("v2_flexibel", "schwarz"),
    "das_filament/TPU/tpu/v2_flexibel_wei": ("v2_flexibel", "wei"),

    # das_filament — PLA Toms3D (1 variant)
    "das_filament/PLA/pla/toms3d_infinity_blue": ("toms3d", "infinity_blue"),

    # =======================================================================
    # recreus — PP 3D (2 variants)
    # =======================================================================
    "recreus/PP/pp/3d_black": ("3d", "black"),
    "recreus/PP/pp/3d_natural": ("3d", "natural"),

    # =======================================================================
    # fiberthree — F3 PA-GF30 (3 variants with colors)
    # =======================================================================
    "fiberthree/PA6/gf_pa6/f3_pa_gf30": ("f3_pa_gf30", "black"),
    "fiberthree/PA6/gf_pa6/f3_pa_gf30_red": ("f3_pa_gf30", "red"),
    "fiberthree/PA6/gf_pa6/f3_pa_gf30_yellow": ("f3_pa_gf30", "yellow"),

    # fiberthree — single-product entries
    "fiberthree/PA12/pa12/f3_pa_pure_lite": ("f3_pa_pure_lite", "natural"),
    "fiberthree/PA12/cf_pa12/f3_pa_cf_lite": ("f3_pa_cf_lite", "black"),
    "fiberthree/PA6/pa6/f3_pa_esd": ("f3_pa_esd", "black"),
    "fiberthree/PA6/pa6/f3_pa_pure": ("f3_pa_pure", "natural"),
    "fiberthree/PA6/pa6/f3_pa_ortho": ("f3_pa_ortho", "natural"),
    "fiberthree/PA6/cf_pa6/f3_pa_cf": ("f3_pa_cf", "black"),
    "fiberthree/PA6/gf_pa6/f3_pa_gf": ("f3_pa_gf", "natural"),
    "fiberthree/PC/cf_pc/f3_cf_150": ("f3_cf_150", "black"),
    "fiberthree/PLA/gf_pla/f3_gf": ("f3_gf", "black"),
    "fiberthree/PP/gf_pp/f3_gf_25": ("f3_gf_25", "black"),
    "fiberthree/TPU/tpu/f3_80a_red": ("f3_80a", "red"),
    "fiberthree/TPU/tpu/f3_98a_black": ("f3_98a", "black"),

    # =======================================================================
    # smart_materials_3d — EP Easy Print (2 variants)
    # =======================================================================
    "smart_materials_3d/PLA/pla/ep_easy_print_ivory_white": ("ep_easy_print", "ivory_white"),
    "smart_materials_3d/PLA/pla/ep_easy_print_true_black": ("ep_easy_print", "true_black"),

    # smart_materials_3d — Iris (5 variants)
    "smart_materials_3d/PLA/pla/iris_alexandrite": ("iris", "alexandrite"),
    "smart_materials_3d/PLA/pla/iris_granate": ("iris", "granate"),
    "smart_materials_3d/PLA/pla/iris_pearl": ("iris", "pearl"),
    "smart_materials_3d/PLA/pla/iris_tanzanite": ("iris", "tanzanite"),
    "smart_materials_3d/PLA/pla/iris_topaz": ("iris", "topaz"),

    # =======================================================================
    # overture — PLA product lines
    # =======================================================================

    # overture — Easy PLA (24 variants)
    "overture/PLA/pla/easy_beige": ("easy", "beige"),
    "overture/PLA/pla/easy_black": ("easy", "black"),
    "overture/PLA/pla/easy_caramel": ("easy", "caramel"),
    "overture/PLA/pla/easy_cobalt_blue": ("easy", "cobalt_blue"),
    "overture/PLA/pla/easy_digital_blue": ("easy", "digital_blue"),
    "overture/PLA/pla/easy_green": ("easy", "green"),
    "overture/PLA/pla/easy_magenta": ("easy", "magenta"),
    "overture/PLA/pla/easy_natural": ("easy", "natural"),
    "overture/PLA/pla/easy_orange": ("easy", "orange"),
    "overture/PLA/pla/easy_pine_green": ("easy", "pine_green"),
    "overture/PLA/pla/easy_pink": ("easy", "pink"),
    "overture/PLA/pla/easy_pumpkin_orange": ("easy", "pumpkin_orange"),
    "overture/PLA/pla/easy_purple": ("easy", "purple"),
    "overture/PLA/pla/easy_red": ("easy", "red"),
    "overture/PLA/pla/easy_rock_white": ("easy", "rock_white"),
    "overture/PLA/pla/easy_shimmer_bronze": ("easy", "shimmer_bronze"),
    "overture/PLA/pla/easy_shimmer_dark_green": ("easy", "shimmer_dark_green"),
    "overture/PLA/pla/easy_shimmer_purple": ("easy", "shimmer_purple"),
    "overture/PLA/pla/easy_shimmer_silver_green": ("easy", "shimmer_silver_green"),
    "overture/PLA/pla/easy_sky_blue": ("easy", "sky_blue"),
    "overture/PLA/pla/easy_space_gray": ("easy", "space_gray"),
    "overture/PLA/pla/easy_white": ("easy", "white"),
    "overture/PLA/pla/easy_yellow": ("easy", "yellow"),
    "overture/PLA/pla/easy_yolk_yellow": ("easy", "yolk_yellow"),

    # overture — Professional PLA (29 variants)
    "overture/PLA/pla/professional_army_green": ("professional", "army_green"),
    "overture/PLA/pla/professional_black": ("professional", "black"),
    "overture/PLA/pla/professional_bronze": ("professional", "bronze"),
    "overture/PLA/pla/professional_brown": ("professional", "brown"),
    "overture/PLA/pla/professional_champagne": ("professional", "champagne"),
    "overture/PLA/pla/professional_chocolate": ("professional", "chocolate"),
    "overture/PLA/pla/professional_copper": ("professional", "copper"),
    "overture/PLA/pla/professional_dark_blue": ("professional", "dark_blue"),
    "overture/PLA/pla/professional_digital_blue": ("professional", "digital_blue"),
    "overture/PLA/pla/professional_fresh_red": ("professional", "fresh_red"),
    "overture/PLA/pla/professional_gray_blue": ("professional", "gray_blue"),
    "overture/PLA/pla/professional_green": ("professional", "green"),
    "overture/PLA/pla/professional_highlight_yellow": ("professional", "highlight_yellow"),
    "overture/PLA/pla/professional_light_blue": ("professional", "light_blue"),
    "overture/PLA/pla/professional_light_gray": ("professional", "light_gray"),
    "overture/PLA/pla/professional_light_green": ("professional", "light_green"),
    "overture/PLA/pla/professional_moonlight_silver": ("professional", "moonlight_silver"),
    "overture/PLA/pla/professional_olive_green": ("professional", "olive_green"),
    "overture/PLA/pla/professional_orange": ("professional", "orange"),
    "overture/PLA/pla/professional_pink": ("professional", "pink"),
    "overture/PLA/pla/professional_purple": ("professional", "purple"),
    "overture/PLA/pla/professional_red": ("professional", "red"),
    "overture/PLA/pla/professional_royal_gold": ("professional", "royal_gold"),
    "overture/PLA/pla/professional_silver_metal": ("professional", "silver_metal"),
    "overture/PLA/pla/professional_space_gray": ("professional", "space_gray"),
    "overture/PLA/pla/professional_sunset_rainbow": ("professional", "sunset_rainbow"),
    "overture/PLA/pla/professional_white": ("professional", "white"),
    "overture/PLA/pla/professional_wine": ("professional", "wine"),
    "overture/PLA/pla/professional_yellow": ("professional", "yellow"),

    # overture — Turbo Rapid PLA (8 variants)
    "overture/PLA/pla/turbo_rapid_black": ("turbo_rapid", "black"),
    "overture/PLA/pla/turbo_rapid_blue": ("turbo_rapid", "blue"),
    "overture/PLA/pla/turbo_rapid_brown": ("turbo_rapid", "brown"),
    "overture/PLA/pla/turbo_rapid_gray": ("turbo_rapid", "gray"),
    "overture/PLA/pla/turbo_rapid_green": ("turbo_rapid", "green"),
    "overture/PLA/pla/turbo_rapid_marble_gray": ("turbo_rapid", "marble_gray"),
    "overture/PLA/pla/turbo_rapid_red": ("turbo_rapid", "red"),
    "overture/PLA/pla/turbo_rapid_ster_white": ("turbo_rapid", "ster_white"),

    # overture — Air PLA (7 variants)
    "overture/PLA/pla/air_black": ("air", "black"),
    "overture/PLA/pla/air_light_gray": ("air", "light_gray"),
    "overture/PLA/pla/air_neon_green": ("air", "neon_green"),
    "overture/PLA/pla/air_orange": ("air", "orange"),
    "overture/PLA/pla/air_white": ("air", "white"),
    "overture/PLA/pla/air_wood": ("air", "wood"),
    "overture/PLA/pla/air_yellow": ("air", "yellow"),

    # overture — Super PLA (12 variants)
    "overture/PLA/pla/super_black": ("super", "black"),
    "overture/PLA/pla/super_dark_blue": ("super", "dark_blue"),
    "overture/PLA/pla/super_green": ("super", "green"),
    "overture/PLA/pla/super_light_brown": ("super", "light_brown"),
    "overture/PLA/pla/super_light_gray": ("super", "light_gray"),
    "overture/PLA/pla/super_orange": ("super", "orange"),
    "overture/PLA/pla/super_pink": ("super", "pink"),
    "overture/PLA/pla/super_purple": ("super", "purple"),
    "overture/PLA/pla/super_red": ("super", "red"),
    "overture/PLA/pla/super_sakura_pink": ("super", "sakura_pink"),
    "overture/PLA/pla/super_white": ("super", "white"),
    "overture/PLA/pla/super_yellow": ("super", "yellow"),

    # overture — Cream PLA (14 variants)
    "overture/PLA/pla/cream_black": ("cream", "black"),
    "overture/PLA/pla/cream_blue": ("cream", "blue"),
    "overture/PLA/pla/cream_grass_green": ("cream", "grass_green"),
    "overture/PLA/pla/cream_gray": ("cream", "gray"),
    "overture/PLA/pla/cream_green": ("cream", "green"),
    "overture/PLA/pla/cream_light_blue": ("cream", "light_blue"),
    "overture/PLA/pla/cream_light_brown": ("cream", "light_brown"),
    "overture/PLA/pla/cream_light_gray": ("cream", "light_gray"),
    "overture/PLA/pla/cream_orange": ("cream", "orange"),
    "overture/PLA/pla/cream_pink": ("cream", "pink"),
    "overture/PLA/pla/cream_purple": ("cream", "purple"),
    "overture/PLA/pla/cream_red": ("cream", "red"),
    "overture/PLA/pla/cream_white": ("cream", "white"),
    "overture/PLA/pla/cream_yellow": ("cream", "yellow"),

    # overture — Easy Glow PLA (4 variants, from glow_pla/)
    "overture/PLA/glow_pla/easy_glow_blue": ("easy_glow", "blue"),
    "overture/PLA/glow_pla/easy_glow_orange": ("easy_glow", "orange"),
    "overture/PLA/glow_pla/easy_glow_red": ("easy_glow", "red"),
    "overture/PLA/glow_pla/easy_glow_yellow": ("easy_glow", "yellow"),

    # overture — Professional PC (4 variants)
    "overture/PC/pc/professional_black": ("professional", "black"),
    "overture/PC/pc/professional_blue": ("professional", "blue"),
    "overture/PC/pc/professional_transparent": ("professional", "transparent"),
    "overture/PC/pc/professional_white": ("professional", "white"),

    # =======================================================================
    # cc3d — Max PLA (7 variants)
    # =======================================================================
    "cc3d/PLA/pla/max_black": ("max", "black"),
    "cc3d/PLA/pla/max_bone_white": ("max", "bone_white"),
    "cc3d/PLA/pla/max_egg_brown": ("max", "egg_brown"),
    "cc3d/PLA/pla/max_flame_orange": ("max", "flame_orange"),
    "cc3d/PLA/pla/max_glory_blue": ("max", "glory_blue"),
    "cc3d/PLA/pla/max_grey": ("max", "grey"),
    "cc3d/PLA/pla/max_ocean_blue": ("max", "ocean_blue"),

    # =======================================================================
    # kingroon — Basic PLA (14 variants)
    # =======================================================================
    "kingroon/PLA/pla/basic_black": ("basic", "black"),
    "kingroon/PLA/pla/basic_blue": ("basic", "blue"),
    "kingroon/PLA/pla/basic_brown": ("basic", "brown"),
    "kingroon/PLA/pla/basic_gray": ("basic", "gray"),
    "kingroon/PLA/pla/basic_green": ("basic", "green"),
    "kingroon/PLA/pla/basic_orange": ("basic", "orange"),
    "kingroon/PLA/pla/basic_pink": ("basic", "pink"),
    "kingroon/PLA/pla/basic_purple": ("basic", "purple"),
    "kingroon/PLA/pla/basic_red": ("basic", "red"),
    "kingroon/PLA/pla/basic_silver": ("basic", "silver"),
    "kingroon/PLA/pla/basic_skin": ("basic", "skin"),
    "kingroon/PLA/pla/basic_transparent": ("basic", "transparent"),
    "kingroon/PLA/pla/basic_white": ("basic", "white"),
    "kingroon/PLA/pla/basic_yellow": ("basic", "yellow"),

    # =======================================================================
    # paramount_3d — Flex PLA (15 variants)
    # =======================================================================
    "paramount_3d/PLA/pla/flex_autobot_blue": ("flex", "autobot_blue"),
    "paramount_3d/PLA/pla/flex_black": ("flex", "black"),
    "paramount_3d/PLA/pla/flex_british_racing_green": ("flex", "british_racing_green"),
    "paramount_3d/PLA/pla/flex_enzo_red": ("flex", "enzo_red"),
    "paramount_3d/PLA/pla/flex_graphite_gray": ("flex", "graphite_gray"),
    "paramount_3d/PLA/pla/flex_harajuku_pink": ("flex", "harajuku_pink"),
    "paramount_3d/PLA/pla/flex_iron_red": ("flex", "iron_red"),
    "paramount_3d/PLA/pla/flex_military_green": ("flex", "military_green"),
    "paramount_3d/PLA/pla/flex_military_khaki": ("flex", "military_khaki"),
    "paramount_3d/PLA/pla/flex_prototype_gray": ("flex", "prototype_gray"),
    "paramount_3d/PLA/pla/flex_skin_dark_complexion": ("flex", "skin_dark_complexion"),
    "paramount_3d/PLA/pla/flex_skin_fair_complexion": ("flex", "skin_fair_complexion"),
    "paramount_3d/PLA/pla/flex_skin_ivory": ("flex", "skin_ivory"),
    "paramount_3d/PLA/pla/flex_skin_universal_beige": ("flex", "skin_universal_beige"),
    "paramount_3d/PLA/pla/flex_white": ("flex", "white"),
}


# ---------------------------------------------------------------------------
# Display name overrides for new filament_type directories
# ---------------------------------------------------------------------------

FILAMENT_NAME_OVERRIDES: dict[str, str] = {
    "850": "850",
    "silk_850": "Silk 850",
    "700": "700",
    "3dxtech": "3DXTech",
    "3dxmax": "3DXMax",
    "3dxstat_esd": "3DXStat ESD",
    "3dxstat_emi": "3DXStat EMI",
    "3dxflex": "3DXFlex",
    "3dxflex_gf30": "3DXFlex GF30",
    "asa_275": "ASA 275",
    "abs_gp450": "ABS GP450",
    "a95": "A95",
    "ht110": "HT110",
    "32_rubberjet_flex": "32 Rubberjet Flex",
    "88_rubberjet_flex": "88 Rubberjet Flex",
    "96": "96",
    "vo3d_high_impact": "VO3D High Impact",
    "3d850": "3D850",
    "3d870": "3D870",
    "nx2_matt": "NX2 Matt",
    "ul94_v0": "UL94 V0",
    "petg_v0": "PETG V0",
    "v0_fr": "V0 FR",
    "5kevlar": "5Kevlar",
    "2": "2",
    "v2_flexibel": "V2 Flexibel",
    "toms3d": "Toms3D",
    "3d": "3D",
    "f3_pa_gf30": "F3 PA-GF30",
    "f3_pa_pure_lite": "F3 PA Pure Lite",
    "f3_pa_cf_lite": "F3 PA CF Lite",
    "f3_pa_esd": "F3 PA ESD",
    "f3_pa_pure": "F3 PA Pure",
    "f3_pa_ortho": "F3 PA Ortho",
    "f3_pa_cf": "F3 PA CF",
    "f3_pa_gf": "F3 PA GF",
    "f3_cf_150": "F3 CF 150",
    "f3_gf": "F3 GF",
    "f3_gf_25": "F3 GF 25",
    "f3_80a": "F3 80A",
    "f3_98a": "F3 98A",
    "ep_easy_print": "EP Easy Print",
    "iris": "Iris",
    "easy": "Easy",
    "professional": "Professional",
    "turbo_rapid": "Turbo Rapid",
    "air": "Air",
    "super": "Super",
    "cream": "Cream",
    "easy_glow": "Easy Glow",
    "max": "Max",
    "basic": "Basic",
    "flex": "Flex",
}


# ---------------------------------------------------------------------------
# Display name overrides for variant IDs where make_display_name isn't enough
# ---------------------------------------------------------------------------

VARIANT_NAME_OVERRIDES: dict[str, str] = {
    "95a_black": "95A Black",
    "85a_black": "85A Black",
    "pc_black": "PC Black",
    "nylon_12_black": "Nylon 12 Black",
    "ultem_1010_black": "Ultem 1010 Black",
    "a_black": "A Black",
    "flex_90a_black": "Flex 90A Black",
    "militar_tone_1_gc": "Militar Tone 1 GC",
}


# ---------------------------------------------------------------------------
# Duplicates to delete (target already exists in the proper directory)
# ---------------------------------------------------------------------------

DUPLICATES_TO_DELETE = [
    # spectrum — ASA 275 (already exist in asa_275/)
    "spectrum/ASA/asa/275_bloody_red",
    "spectrum/ASA/asa/275_brown_red",
    "spectrum/ASA/asa/275_dark_grey",
    "spectrum/ASA/asa/275_deep_black",
    "spectrum/ASA/asa/275_forest_green",
    "spectrum/ASA/asa/275_lime_green",
    "spectrum/ASA/asa/275_lion_orange",
    "spectrum/ASA/asa/275_natural",
    "spectrum/ASA/asa/275_navy_blue",
    "spectrum/ASA/asa/275_pacific_blue",
    "spectrum/ASA/asa/275_polar_white",
    "spectrum/ASA/asa/275_silver_star",
    "spectrum/ASA/asa/275_traffic_yellow",

    # spectrum — ABS GP450 (already exist in abs_gp450/)
    "spectrum/ABS/abs/gp450_dark_blue",
    "spectrum/ABS/abs/gp450_natural",
    "spectrum/ABS/abs/gp450_obsidian_black",
    "spectrum/ABS/abs/gp450_pure_green",
    "spectrum/ABS/abs/gp450_pure_white",
    "spectrum/ABS/abs/gp450_silver",
    "spectrum/ABS/abs/gp450_traffic_red",

    # prusament — PETG V0 (already exist in petg_v0/)
    "prusament/PETG/petg/v0_jet_black",
    "prusament/PETG/petg/v0_natural",

    # overture — Rock PLA (already exist in pla_rock/)
    "overture/PLA/pla/rock_alpine_forest",
    "overture/PLA/pla/rock_barrier_reef",
    "overture/PLA/pla/rock_cheesewood",
    "overture/PLA/pla/rock_desert_bluff",
    "overture/PLA/pla/rock_fossil_rock",
    "overture/PLA/pla/rock_glacier_blue",
    "overture/PLA/pla/rock_haze_gray",
    "overture/PLA/pla/rock_jarrah",
    "overture/PLA/pla/rock_marigold_yellow",
    "overture/PLA/pla/rock_mars_red",
    "overture/PLA/pla/rock_mist_gray",
    "overture/PLA/pla/rock_moonlight_gray",
    "overture/PLA/pla/rock_muted_gray",
    "overture/PLA/pla/rock_painted_hills",
    "overture/PLA/pla/rock_pink_lake",
    "overture/PLA/pla/rock_rock_rainbow",
    "overture/PLA/pla/rock_rock_white",
    "overture/PLA/pla/rock_sedimentary_rock",
    "overture/PLA/pla/rock_sedona_red",
    "overture/PLA/pla/rock_slate_gray",
    "overture/PLA/pla/rock_tropical_jungle",
    "overture/PLA/pla/rock_walnut_wood",
    "overture/PLA/pla/rock_wetland_green",
    "overture/PLA/pla/rock_white_oak",

    # bambu_lab — Basic PLA (already exist in basic/)
    "bambu_lab/PLA/pla/basic_bambu_green",
    "bambu_lab/PLA/pla/basic_beige",
    "bambu_lab/PLA/pla/basic_black",
    "bambu_lab/PLA/pla/basic_blue",
    "bambu_lab/PLA/pla/basic_blue_grey",
    "bambu_lab/PLA/pla/basic_bright_green",
    "bambu_lab/PLA/pla/basic_bronze",
    "bambu_lab/PLA/pla/basic_brown",
    "bambu_lab/PLA/pla/basic_cobalt_blue",
    "bambu_lab/PLA/pla/basic_cocoa_brown",
    "bambu_lab/PLA/pla/basic_cyan",
    "bambu_lab/PLA/pla/basic_dark_gray",
    "bambu_lab/PLA/pla/basic_gold",
    "bambu_lab/PLA/pla/basic_gray",
    "bambu_lab/PLA/pla/basic_hot_pink",
    "bambu_lab/PLA/pla/basic_indigo_purple",
    "bambu_lab/PLA/pla/basic_jade_white",
    "bambu_lab/PLA/pla/basic_light_gray",
    "bambu_lab/PLA/pla/basic_magenta",
    "bambu_lab/PLA/pla/basic_maroon_red",
    "bambu_lab/PLA/pla/basic_mistletoe_green",
    "bambu_lab/PLA/pla/basic_orange",
    "bambu_lab/PLA/pla/basic_pink",
    "bambu_lab/PLA/pla/basic_pumpkin_orange",
    "bambu_lab/PLA/pla/basic_purple",
    "bambu_lab/PLA/pla/basic_red",
    "bambu_lab/PLA/pla/basic_silver",
    "bambu_lab/PLA/pla/basic_sunflower_yellow",
    "bambu_lab/PLA/pla/basic_turquoise",
    "bambu_lab/PLA/pla/basic_yellow",

    # bambu_lab — Basic Gradient PLA (already exist in basic_gradient/)
    "bambu_lab/PLA/pla/basic_gradient_arctic_whisper",
    "bambu_lab/PLA/pla/basic_gradient_blueberry_bubblegum",
    "bambu_lab/PLA/pla/basic_gradient_cotton_candy_cloud",
    "bambu_lab/PLA/pla/basic_gradient_dusk_glare",
    "bambu_lab/PLA/pla/basic_gradient_mint_lime",
    "bambu_lab/PLA/pla/basic_gradient_ocean_to_meadow",
    "bambu_lab/PLA/pla/basic_gradient_pink_citrus",
    "bambu_lab/PLA/pla/basic_gradient_solar_breeze",

    # bambu_lab — HF PETG (already exist in hf/)
    "bambu_lab/PETG/petg/hf_black",
    "bambu_lab/PETG/petg/hf_blue",
    "bambu_lab/PETG/petg/hf_cream",
    "bambu_lab/PETG/petg/hf_dark_gray",
    "bambu_lab/PETG/petg/hf_forest_green",
    "bambu_lab/PETG/petg/hf_gray",
    "bambu_lab/PETG/petg/hf_green",
    "bambu_lab/PETG/petg/hf_lake_blue",
    "bambu_lab/PETG/petg/hf_lime_green",
    "bambu_lab/PETG/petg/hf_orange",
    "bambu_lab/PETG/petg/hf_peanut_brown",
    "bambu_lab/PETG/petg/hf_red",
    "bambu_lab/PETG/petg/hf_white",
    "bambu_lab/PETG/petg/hf_yellow",

    # bambu_lab — Marble PLA (already exist in marble/)
    "bambu_lab/PLA/pla/marble_red_granite",
    "bambu_lab/PLA/pla/marble_white_marble",

    # bambu_lab — Metal PLA (already exist in metal/)
    "bambu_lab/PLA/pla/metal_copper_brown_metallic",
    "bambu_lab/PLA/pla/metal_iridium_gold_metallic",
    "bambu_lab/PLA/pla/metal_iron_gray_metallic",

    # bambu_lab — Sparkle PLA (already exist in sparkle/)
    "bambu_lab/PLA/pla/sparkle_alpine_green",
    "bambu_lab/PLA/pla/sparkle_classic_gold",
    "bambu_lab/PLA/pla/sparkle_crimson_red",
    "bambu_lab/PLA/pla/sparkle_onyx_black",
    "bambu_lab/PLA/pla/sparkle_royal_purple",
    "bambu_lab/PLA/pla/sparkle_slate_gray",

    # elegoo — Plus PLA (already exist in pla_plus/)
    "elegoo/PLA/pla/plus_beige",
    "elegoo/PLA/pla/plus_black",
    "elegoo/PLA/pla/plus_brown",
    "elegoo/PLA/pla/plus_clear",
    "elegoo/PLA/pla/plus_dark_blue",
    "elegoo/PLA/pla/plus_grey",
    "elegoo/PLA/pla/plus_neon_green",
    "elegoo/PLA/pla/plus_orange",
    "elegoo/PLA/pla/plus_pink",
    "elegoo/PLA/pla/plus_purple",
    "elegoo/PLA/pla/plus_red",
    "elegoo/PLA/pla/plus_sea_green",
    "elegoo/PLA/pla/plus_sky_blue",
    "elegoo/PLA/pla/plus_space_grey",
    "elegoo/PLA/pla/plus_white",
    "elegoo/PLA/pla/plus_wood_color",
    "elegoo/PLA/pla/plus_yellow",
]


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------

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

    variant_name = VARIANT_NAME_OVERRIDES.get(
        new_variant_id, make_display_name(new_variant_id))
    filament_name = FILAMENT_NAME_OVERRIDES.get(
        new_filament_id, make_display_name(new_filament_id))

    print(f"  SPLIT:  {old_rel}")
    print(f"      -> .../{new_filament_id}/{new_variant_id}"
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


def do_delete_duplicate(data_dir: Path, old_rel: str, dry_run: bool) -> bool:
    """Delete a duplicate variant directory (target already exists)."""
    old_path = data_dir / old_rel
    if not old_path.is_dir():
        print(f"  NOT FOUND: {old_rel}")
        return False

    print(f"  DELETE: {old_rel}  (duplicate)")

    if dry_run:
        return True

    shutil.rmtree(str(old_path))
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Split product-line prefixes from variant names into "
                    "filament_type directories")
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
    print(f"PRODUCT LINE SPLITS — {mode}")
    print(f"{'=' * 60}\n")

    ok = 0
    fail = 0

    print(f"SPLITS ({len(PRODUCT_LINE_SPLITS)}):")
    print("-" * 40)

    current_brand = ""
    for old_rel, (fil_id, var_id) in PRODUCT_LINE_SPLITS.items():
        brand = old_rel.split("/")[0]
        if brand != current_brand:
            current_brand = brand
            print(f"\n  [{brand}]")
        if do_product_line_split(data_dir, old_rel, fil_id, var_id, dry_run):
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

    # --- Summary ---
    total = len(PRODUCT_LINE_SPLITS) + len(DUPLICATES_TO_DELETE)
    print(f"\n{'=' * 60}")
    print(f"Mode:      {mode}")
    print(f"Success:   {ok}")
    print(f"Failed:    {fail}")
    print(f"Total:     {total}")
    print(f"{'=' * 60}")

    if dry_run and fail == 0:
        print("\nRe-run with --apply to execute these changes.")

    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

"""
Import OpenPrintTag Script - Import data from OpenPrintTag database.

This script downloads the OpenPrintTag database from GitHub and imports
the data into the Open Filament Database format, merging with existing
data without overwriting.
"""

import argparse
import json
import os
import re
import subprocess
import urllib.parse
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Optional

import requests
import yaml

from ofd.base import BaseScript, ScriptResult, register_script

# OpenPrintTag repository URL
OPENPRINTTAG_REPO = "https://github.com/OpenPrintTag/openprinttag-database.git"

# Default material densities (g/cm³)
DENSITY_DEFAULTS: dict[str, float] = {
    "PLA": 1.24,
    "PETG": 1.27,
    "ABS": 1.04,
    "ASA": 1.07,
    "TPU": 1.21,
    "TPE": 1.20,
    "PA": 1.14,
    "PA6": 1.14,
    "PA11": 1.03,
    "PA12": 1.01,
    "PA66": 1.14,
    "PC": 1.20,
    "PCTG": 1.23,
    "PVA": 1.23,
    "BVOH": 1.14,
    "HIPS": 1.04,
    "PP": 0.90,
    "PEI": 1.27,
    "PEEK": 1.30,
    "PEKK": 1.30,
    "PVB": 1.08,
    "CPE": 1.25,
    "PET": 1.38,
}

# Default temperatures by material type (°C)
TEMPERATURE_DEFAULTS: dict[str, dict[str, int]] = {
    "PLA": {
        "min_print_temperature": 190,
        "max_print_temperature": 230,
        "min_bed_temperature": 50,
        "max_bed_temperature": 70,
    },
    "PETG": {
        "min_print_temperature": 220,
        "max_print_temperature": 250,
        "min_bed_temperature": 70,
        "max_bed_temperature": 90,
    },
    "ABS": {
        "min_print_temperature": 230,
        "max_print_temperature": 260,
        "min_bed_temperature": 90,
        "max_bed_temperature": 110,
    },
    "ASA": {
        "min_print_temperature": 235,
        "max_print_temperature": 260,
        "min_bed_temperature": 90,
        "max_bed_temperature": 110,
    },
    "TPU": {
        "min_print_temperature": 210,
        "max_print_temperature": 240,
        "min_bed_temperature": 30,
        "max_bed_temperature": 60,
    },
    "TPE": {
        "min_print_temperature": 210,
        "max_print_temperature": 240,
        "min_bed_temperature": 30,
        "max_bed_temperature": 60,
    },
    "PA": {
        "min_print_temperature": 240,
        "max_print_temperature": 280,
        "min_bed_temperature": 80,
        "max_bed_temperature": 100,
    },
    "PA6": {
        "min_print_temperature": 250,
        "max_print_temperature": 290,
        "min_bed_temperature": 80,
        "max_bed_temperature": 100,
    },
    "PA11": {
        "min_print_temperature": 240,
        "max_print_temperature": 270,
        "min_bed_temperature": 80,
        "max_bed_temperature": 100,
    },
    "PA12": {
        "min_print_temperature": 240,
        "max_print_temperature": 270,
        "min_bed_temperature": 80,
        "max_bed_temperature": 100,
    },
    "PA66": {
        "min_print_temperature": 260,
        "max_print_temperature": 300,
        "min_bed_temperature": 90,
        "max_bed_temperature": 110,
    },
    "PC": {
        "min_print_temperature": 260,
        "max_print_temperature": 300,
        "min_bed_temperature": 100,
        "max_bed_temperature": 120,
    },
    "PCTG": {
        "min_print_temperature": 230,
        "max_print_temperature": 260,
        "min_bed_temperature": 70,
        "max_bed_temperature": 90,
    },
    "PVA": {
        "min_print_temperature": 180,
        "max_print_temperature": 210,
        "min_bed_temperature": 50,
        "max_bed_temperature": 60,
    },
    "BVOH": {
        "min_print_temperature": 190,
        "max_print_temperature": 220,
        "min_bed_temperature": 50,
        "max_bed_temperature": 70,
    },
    "HIPS": {
        "min_print_temperature": 220,
        "max_print_temperature": 250,
        "min_bed_temperature": 90,
        "max_bed_temperature": 110,
    },
    "PP": {
        "min_print_temperature": 210,
        "max_print_temperature": 240,
        "min_bed_temperature": 80,
        "max_bed_temperature": 100,
    },
    "PEI": {
        "min_print_temperature": 340,
        "max_print_temperature": 380,
        "min_bed_temperature": 120,
        "max_bed_temperature": 160,
    },
    "PEEK": {
        "min_print_temperature": 360,
        "max_print_temperature": 420,
        "min_bed_temperature": 120,
        "max_bed_temperature": 160,
    },
    "PEKK": {
        "min_print_temperature": 350,
        "max_print_temperature": 400,
        "min_bed_temperature": 120,
        "max_bed_temperature": 160,
    },
    "PVB": {
        "min_print_temperature": 190,
        "max_print_temperature": 220,
        "min_bed_temperature": 50,
        "max_bed_temperature": 75,
    },
    "CPE": {
        "min_print_temperature": 240,
        "max_print_temperature": 270,
        "min_bed_temperature": 70,
        "max_bed_temperature": 90,
    },
    "PET": {
        "min_print_temperature": 220,
        "max_print_temperature": 250,
        "min_bed_temperature": 70,
        "max_bed_temperature": 90,
    },
}

# Brands to ignore during import (test/placeholder brands)
IGNORED_BRANDS: set[str] = {
    "fake_company",
    "generic",
}

# Tag to trait mapping (OPT tags -> internal traits)
TAG_TO_TRAIT_MAP: dict[str, str] = {
    # Visual properties
    "silk": "silk",
    "matte": "matte",
    "glow_in_the_dark": "glow",
    "translucent": "translucent",
    "transparent": "transparent",
    "glitter": "glitter",
    "neon": "neon",
    "iridescent": "iridescent",
    "pearlescent": "pearlescent",
    "coextruded": "coextruded",
    "gradual_color_change": "gradual_color_change",
    "temperature_color_change": "temperature_color_change",
    "illuminescent_color_change": "illuminescent_color_change",
    "without_pigments": "without_pigments",
    "lithophane": "lithophane",
    "limited_edition": "limited_edition",
    # Material properties
    "recycled": "recycled",
    "recyclable": "recyclable",
    "biodegradable": "biodegradable",
    "bio_based": "bio_based",
    "biocompatible": "biocompatible",
    "home_compostable": "home_compostable",
    "industrially_compostable": "industrially_compostable",
    "antibacterial": "antibacterial",
    # Technical properties
    "abrasive": "abrasive",
    "filtration_recommended": "filtration_recommended",
    "esd_safe": "esd_safe",
    "conductive": "conductive",
    "emi_shielding": "emi_shielding",
    "water_soluble": "water_soluble",
    "ipa_soluble": "ipa_soluble",
    "limonene_soluble": "limonene_soluble",
    "self_extinguishing": "self_extinguishing",
    "high_temperature": "high_temperature",
    "low_outgassing": "low_outgassing",
    "foaming": "foaming",
    "castable": "castable",
    "blend": "blend",
    "paramagnetic": "paramagnetic",
    "radiation_shielding": "radiation_shielding",
    "air_filtering": "air_filtering",
    # Material composition
    "contains_carbon": "contains_carbon",
    "contains_carbon_fiber": "contains_carbon_fiber",
    "contains_carbon_nano_tubes": "contains_carbon_nano_tubes",
    "contains_glass": "contains_glass",
    "contains_glass_fiber": "contains_glass_fiber",
    "contains_kevlar": "contains_kevlar",
    "contains_wood": "contains_wood",
    "contains_bamboo": "contains_bamboo",
    "contains_cork": "contains_cork",
    "contains_metal": "contains_metal",
    "contains_bronze": "contains_bronze",
    "contains_copper": "contains_copper",
    "contains_iron": "contains_iron",
    "contains_steel": "contains_steel",
    "contains_aluminium": "contains_aluminium",
    "contains_stone": "contains_stone",
    "contains_ceramic": "contains_ceramic",
    "contains_magnetite": "contains_magnetite",
    "contains_wax": "contains_wax",
    "contains_algae": "contains_algae",
    "contains_pine": "contains_pine",
    "contains_graphene": "contains_graphene",
    # Imitation
    "imitates_wood": "imitates_wood",
    "imitates_metal": "imitates_metal",
    "imitates_marble": "imitates_marble",
    "imitates_stone": "imitates_stone",
}


@dataclass
class ImportReport:
    """Tracks import statistics and missing data."""

    brands_imported: int = 0
    brands_merged: int = 0
    brands_skipped: int = 0
    materials_imported: int = 0
    filaments_created: int = 0
    variants_created: int = 0
    sizes_created: int = 0

    missing_websites: list[str] = field(default_factory=list)
    missing_logos: list[str] = field(default_factory=list)
    missing_density: list[str] = field(default_factory=list)
    missing_temperatures: list[str] = field(default_factory=list)
    parse_warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    fuzzy_matches: list[str] = field(default_factory=list)

    def generate_report(self) -> str:
        """Generate a human-readable report showing only issues."""
        lines = [
            "=" * 60,
            "OPENPRINTTAG IMPORT REPORT - ISSUES",
            "=" * 60,
            "",
        ]

        has_issues = False

        if self.errors:
            has_issues = True
            lines.append(f"ERRORS ({len(self.errors)}):")
            for err in self.errors:
                lines.append(f"   - {err}")
            lines.append("")

        if self.missing_websites:
            has_issues = True
            lines.append(f"MISSING WEBSITES ({len(self.missing_websites)}):")
            for brand in self.missing_websites:
                lines.append(f"   - {brand}")
            lines.append("")

        if self.missing_logos:
            has_issues = True
            lines.append(f"MISSING LOGOS ({len(self.missing_logos)}):")
            for brand in self.missing_logos:
                lines.append(f"   - {brand}")
            lines.append("")

        if self.missing_temperatures:
            has_issues = True
            lines.append(f"MISSING TEMPERATURE DATA ({len(self.missing_temperatures)}):")
            for item in self.missing_temperatures:
                lines.append(f"   - {item}")
            lines.append("")

        if self.parse_warnings:
            has_issues = True
            lines.append(f"PARSE WARNINGS ({len(self.parse_warnings)}):")
            for warn in self.parse_warnings:
                lines.append(f"   - {warn}")
            lines.append("")

        if self.fuzzy_matches:
            has_issues = True
            lines.append(f"FUZZY MATCHES (verify these are correct) ({len(self.fuzzy_matches)}):")
            for match in self.fuzzy_matches:
                lines.append(f"   - {match}")
            lines.append("")

        if not has_issues:
            lines.append("No issues found!")
            lines.append("")

        # Summary line
        lines.append("-" * 60)
        lines.append(
            f"Summary: {self.brands_imported} new, {self.brands_merged} merged, "
            f"{self.brands_skipped} skipped, {self.variants_created} variants"
        )

        return "\n".join(lines)


def slugify(text: str) -> str:
    """Convert text to a valid ID (lowercase, underscores)."""
    # Convert to lowercase
    text = text.lower()
    # Replace hyphens and spaces with underscores
    text = re.sub(r"[-\s]+", "_", text)
    # Remove invalid characters (keep only alphanumeric and underscore)
    text = re.sub(r"[^a-z0-9_]", "", text)
    # Remove leading/trailing underscores
    text = text.strip("_")
    # Collapse multiple underscores
    text = re.sub(r"_+", "_", text)
    return text or "default"


def convert_rgba_to_rgb(rgba: Optional[str]) -> str:
    """Convert RGBA hex to RGB hex (strip alpha channel)."""
    if not rgba:
        return "#000000"

    # Remove leading #
    hex_str = rgba.lstrip("#")

    # Extract RGB (first 6 chars), ignore alpha (last 2)
    if len(hex_str) >= 6:
        rgb = hex_str[:6].upper()
        return f"#{rgb}"

    return "#000000"


def microns_to_mm(microns: int) -> float:
    """Convert microns to millimeters."""
    return microns / 1000.0


@register_script
class ImportOpenPrintTagScript(BaseScript):
    """Import data from OpenPrintTag database."""

    name = "import_openprinttag"
    description = "Import data from OpenPrintTag database"

    def __init__(self, project_root: Optional[Path] = None):
        super().__init__(project_root)
        self.report = ImportReport()
        self.brandfetch_client_id: Optional[str] = None
        self.brand_aliases: dict[str, str] = {}

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        """Add script-specific arguments."""
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without writing files",
        )
        parser.add_argument(
            "--skip-update",
            action="store_true",
            help="Skip repository update, use cached version",
        )
        parser.add_argument(
            "--skip-brandfetch",
            action="store_true",
            help="Skip Brandfetch logo/website discovery",
        )
        parser.add_argument(
            "--cache-path",
            default=".cache/openprinttag-database",
            help="Path to cached OpenPrintTag repository",
        )
        parser.add_argument(
            "--brand",
            help="Only import specific brand (by slug)",
        )
        parser.add_argument(
            "--report-path",
            default=".cache/openprinttag-import-report.txt",
            help="Path to save import report",
        )

    def run(self, args: argparse.Namespace) -> ScriptResult:
        """Execute the import."""
        dry_run = args.dry_run
        skip_update = args.skip_update
        skip_brandfetch = args.skip_brandfetch
        cache_path = self.project_root / args.cache_path
        brand_filter = args.brand
        report_path = self.project_root / args.report_path

        # Get Brandfetch client ID from environment
        self.brandfetch_client_id = os.environ.get("BRANDFETCH_CLIENT_ID")
        if not self.brandfetch_client_id and not skip_brandfetch:
            self.log("Note: BRANDFETCH_CLIENT_ID not set, skipping logo/website discovery")
            skip_brandfetch = True

        # Load brand aliases for fuzzy matching
        aliases_path = self.data_dir / "brand_aliases.json"
        if aliases_path.exists():
            try:
                with open(aliases_path, encoding="utf-8") as f:
                    self.brand_aliases = json.load(f)
                self.log(f"Loaded {len(self.brand_aliases)} brand aliases")
            except Exception as e:
                self.log(f"Warning: Could not load brand aliases: {e}")

        if dry_run:
            self.log("=== DRY RUN MODE ===\n")

        # Step 1: Ensure repository
        self.emit_progress("repo", 0, "Preparing repository...")
        try:
            self._ensure_repository(cache_path, skip_update)
        except Exception as e:
            return ScriptResult(
                success=False,
                message=f"Failed to prepare repository: {e}",
            )
        self.emit_progress("repo", 100, "Repository ready")

        # Step 2: Load all source data
        self.emit_progress("loading", 0, "Loading OpenPrintTag data...")
        brands = self._load_brands(cache_path)
        materials = self._load_materials(cache_path)
        packages = self._load_packages(cache_path)
        self.log(f"Loaded {len(brands)} brands, {len(materials)} materials, {len(packages)} packages")
        self.emit_progress("loading", 100, "Data loaded")

        # Step 3: Group data by brand
        materials_by_brand = self._group_by_brand(materials)
        packages_by_material = self._group_packages_by_material(packages)

        # Step 4: Process each brand
        self.emit_progress("processing", 0, "Processing brands...")
        total_brands = len(brands)

        for i, (brand_slug, brand_data) in enumerate(brands.items()):
            if brand_filter and brand_slug != brand_filter:
                continue

            progress = int((i / max(total_brands, 1)) * 100)
            self.emit_progress("processing", progress, f"Processing {brand_slug}...")

            self._process_brand(
                brand_slug,
                brand_data,
                materials_by_brand.get(brand_slug, []),
                packages_by_material,
                skip_brandfetch,
                dry_run,
            )

        self.emit_progress("processing", 100, "Processing complete")

        # Step 5: Save report
        report_text = self.report.generate_report()
        self.log("\n" + report_text)

        if not dry_run:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(report_text)
            self.log(f"\nReport saved to: {report_path}")

        return ScriptResult(
            success=True,
            message="Import completed",
            data={
                "brands_imported": self.report.brands_imported,
                "brands_merged": self.report.brands_merged,
                "materials_imported": self.report.materials_imported,
                "variants_created": self.report.variants_created,
            },
        )

    def _ensure_repository(self, cache_path: Path, skip_update: bool) -> None:
        """Clone or update the OpenPrintTag repository."""
        if cache_path.exists() and (cache_path / ".git").exists():
            if not skip_update:
                self.log("Updating OpenPrintTag repository...")
                result = subprocess.run(
                    ["git", "-C", str(cache_path), "pull", "--ff-only"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    self.log(f"Warning: git pull failed: {result.stderr}")
        else:
            self.log("Cloning OpenPrintTag repository...")
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            result = subprocess.run(
                ["git", "clone", "--depth=1", OPENPRINTTAG_REPO, str(cache_path)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(f"git clone failed: {result.stderr}")

    def _load_yaml(self, path: Path) -> Optional[dict[str, Any]]:
        """Load a YAML file."""
        try:
            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.report.errors.append(f"Failed to load {path.name}: {e}")
            return None

    def _load_brands(self, cache_path: Path) -> dict[str, dict]:
        """Load all brand YAML files."""
        brands: dict[str, dict] = {}
        brands_dir = cache_path / "data" / "brands"

        if not brands_dir.exists():
            return brands

        for yaml_file in brands_dir.glob("*.yaml"):
            data = self._load_yaml(yaml_file)
            if data and "slug" in data:
                brands[data["slug"]] = data

        return brands

    def _load_materials(self, cache_path: Path) -> list[dict]:
        """Load all material YAML files."""
        materials: list[dict] = []
        materials_dir = cache_path / "data" / "materials"

        if not materials_dir.exists():
            return materials

        for brand_dir in materials_dir.iterdir():
            if not brand_dir.is_dir():
                continue
            for yaml_file in brand_dir.glob("*.yaml"):
                data = self._load_yaml(yaml_file)
                if data:
                    materials.append(data)

        return materials

    def _load_packages(self, cache_path: Path) -> list[dict]:
        """Load all material package YAML files."""
        packages: list[dict] = []
        packages_dir = cache_path / "data" / "material-packages"

        if not packages_dir.exists():
            return packages

        for brand_dir in packages_dir.iterdir():
            if not brand_dir.is_dir():
                continue
            for yaml_file in brand_dir.glob("*.yaml"):
                data = self._load_yaml(yaml_file)
                if data:
                    packages.append(data)

        return packages

    def _group_by_brand(self, materials: list[dict]) -> dict[str, list[dict]]:
        """Group materials by brand slug."""
        grouped: dict[str, list[dict]] = {}
        for material in materials:
            brand_slug = material.get("brand", {}).get("slug", "")
            if brand_slug:
                if brand_slug not in grouped:
                    grouped[brand_slug] = []
                grouped[brand_slug].append(material)
        return grouped

    def _group_packages_by_material(self, packages: list[dict]) -> dict[str, list[dict]]:
        """Group packages by material slug."""
        grouped: dict[str, list[dict]] = {}
        for package in packages:
            material_slug = package.get("material", {}).get("slug", "")
            if material_slug:
                if material_slug not in grouped:
                    grouped[material_slug] = []
                grouped[material_slug].append(package)
        return grouped

    def _process_brand(
        self,
        brand_slug: str,
        brand_data: dict,
        materials: list[dict],
        packages_by_material: dict[str, list[dict]],
        skip_brandfetch: bool,
        dry_run: bool,
    ) -> None:
        """Process a single brand and its materials."""
        brand_id = slugify(brand_slug)

        # Skip ignored brands (test/placeholder entries)
        if brand_id in IGNORED_BRANDS:
            self.report.brands_skipped += 1
            return
        brand_name = brand_data.get("name", brand_slug)

        # Try to find existing folder using fuzzy matching
        existing_folder = self._find_existing_brand_folder(brand_id, brand_name)
        if existing_folder:
            # Use the existing folder's ID instead of generating new one
            brand_id = existing_folder.name
            brand_dir = existing_folder
        else:
            brand_dir = self.data_dir / brand_id

        # Check for existing brand data
        existing_brand: Optional[dict] = None
        brand_json_path = brand_dir / "brand.json"
        if brand_json_path.exists():
            try:
                with open(brand_json_path, encoding="utf-8") as f:
                    existing_brand = json.load(f)
            except Exception:
                pass

        # Convert OPT brand to internal format
        countries = brand_data.get("countries_of_origin", [])
        origin = countries[0] if countries else "Unknown"

        new_brand = {
            "id": brand_id,
            "name": brand_data.get("name", brand_slug),
            "website": "",
            "logo": "logo.png",
            "origin": origin,
            "source": "openprinttag",
        }

        # Merge with existing (fill gaps only)
        if existing_brand:
            merged_brand = self._merge_data(existing_brand, new_brand)
            self.report.brands_merged += 1
        else:
            merged_brand = new_brand
            self.report.brands_imported += 1

        # Check if we need website/logo
        need_website = not merged_brand.get("website")
        need_logo = True
        for ext in ["png", "jpg", "svg", "jpeg"]:
            if (brand_dir / f"logo.{ext}").exists():
                need_logo = False
                merged_brand["logo"] = f"logo.{ext}"
                break

        # Try Brandfetch if needed
        if not skip_brandfetch and (need_website or need_logo):
            domain = self._discover_domain(merged_brand["name"])
            if domain:
                if need_website:
                    merged_brand["website"] = domain
                if need_logo and not dry_run:
                    logo_ext = self._download_logo(domain, brand_dir)
                    if logo_ext:
                        merged_brand["logo"] = f"logo.{logo_ext}"
                        need_logo = False

        # Track missing data
        if not merged_brand.get("website"):
            self.report.missing_websites.append(brand_id)
        if need_logo:
            self.report.missing_logos.append(brand_id)

        # Write brand.json
        if not dry_run:
            brand_dir.mkdir(parents=True, exist_ok=True)
            self._save_json(brand_json_path, merged_brand)

        # Process materials for this brand
        self._process_materials(
            brand_id,
            brand_dir,
            materials,
            packages_by_material,
            dry_run,
        )

    def _find_existing_brand_folder(
        self, brand_id: str, brand_name: str
    ) -> Optional[Path]:
        """
        Find an existing brand folder using aliases and fuzzy matching.

        Priority order:
        1. Alias from brand_aliases.json (takes precedence, for consolidation)
        2. Exact match
        3. Prefix match (e.g., "prusament_resin" -> "prusament")
        4. Fuzzy match via SequenceMatcher

        Returns the path to the existing folder, or None if no match found.
        """
        # Check for explicit alias mapping FIRST (takes precedence for consolidation)
        if brand_id in self.brand_aliases:
            alias_target = self.brand_aliases[brand_id]
            alias_path = self.data_dir / alias_target
            if alias_path.exists():
                match_info = f"'{brand_id}' -> '{alias_target}' (alias)"
                self.report.fuzzy_matches.append(match_info)
                return alias_path

        # Exact match check
        exact_path = self.data_dir / brand_id
        if exact_path.exists():
            return exact_path

        # Normalize function for comparison - removes underscores, hyphens
        def normalize(s: str) -> str:
            return re.sub(r"[_\-]", "", s.lower())

        normalized_id = normalize(brand_id)
        normalized_name = normalize(brand_name)

        best_prefix_match: Optional[Path] = None
        best_prefix_score: float = 0.0
        best_fuzzy_match: Optional[Path] = None
        best_fuzzy_score: float = 0.0

        for folder in self.data_dir.iterdir():
            if not folder.is_dir():
                continue

            folder_normalized = normalize(folder.name)

            # Check for prefix match: existing folder is prefix of incoming
            # e.g., "prusament" is prefix of "prusamentresin" -> match prusament
            if normalized_id.startswith(folder_normalized) and len(
                folder_normalized
            ) >= 4:
                prefix_score = len(folder_normalized) / len(normalized_id)
                if prefix_score > best_prefix_score:
                    best_prefix_score = prefix_score
                    best_prefix_match = folder
                continue

            # Compare against both ID and name using sequence matcher
            score_id = SequenceMatcher(None, normalized_id, folder_normalized).ratio()
            score_name = SequenceMatcher(
                None, normalized_name, folder_normalized
            ).ratio()
            score = max(score_id, score_name)

            if score > best_fuzzy_score:
                best_fuzzy_score = score
                best_fuzzy_match = folder

        # Threshold for prefix matches (lower, since prefix is a strong signal)
        prefix_threshold = 0.55
        # Threshold for fuzzy matches (higher, to avoid false positives)
        fuzzy_threshold = 0.85

        # Prefer prefix match if good enough
        if best_prefix_match and best_prefix_score >= prefix_threshold:
            match_info = (
                f"'{brand_id}' -> '{best_prefix_match.name}' "
                f"(prefix: {best_prefix_score:.2f})"
            )
            self.report.fuzzy_matches.append(match_info)
            return best_prefix_match

        # Fall back to fuzzy match
        if best_fuzzy_match and best_fuzzy_score >= fuzzy_threshold:
            match_info = (
                f"'{brand_id}' -> '{best_fuzzy_match.name}' "
                f"(fuzzy: {best_fuzzy_score:.2f})"
            )
            self.report.fuzzy_matches.append(match_info)
            return best_fuzzy_match

        return None

    def _merge_data(self, existing: dict, new: dict) -> dict:
        """Merge new data into existing, only filling gaps."""
        result = existing.copy()

        for key, value in new.items():
            existing_value = result.get(key)
            # Only add if missing or empty
            if existing_value is None or existing_value == "" or existing_value == []:
                result[key] = value

        return result

    def _discover_domain(self, brand_name: str) -> Optional[str]:
        """Try to find brand domain using Brandfetch CDN, then search API."""
        if not self.brandfetch_client_id:
            return None

        # Normalize brand name for domain guessing
        normalized = re.sub(r"[^a-z0-9]", "", brand_name.lower())

        # Domain patterns to try
        patterns = [
            f"{normalized}.com",
            f"{normalized}.net",
            f"{normalized}.io",
            f"{normalized}3d.com",
            f"{normalized}filament.com",
            f"{normalized}-filament.com",
        ]

        for domain in patterns:
            url = f"https://cdn.brandfetch.io/{domain}?c={self.brandfetch_client_id}"
            try:
                response = requests.head(url, timeout=5)
                if response.ok:
                    return f"https://{domain}"
            except Exception:
                continue

        # Fallback: try Brandfetch Search API
        return self._search_brandfetch(brand_name)

    def _search_brandfetch(self, brand_name: str) -> Optional[str]:
        """
        Search Brandfetch API for brand domain as fallback.

        Only called when domain pattern guessing fails.
        """
        if not self.brandfetch_client_id:
            return None

        # URL-encode the brand name
        encoded_name = urllib.parse.quote(brand_name)

        url = f"https://api.brandfetch.io/v2/search/{encoded_name}"
        headers = {"Authorization": f"Bearer {self.brandfetch_client_id}"}

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.ok:
                results = response.json()
                # Take the first/best match if available
                if results and isinstance(results, list) and len(results) > 0:
                    first_match = results[0]
                    domain = first_match.get("domain")
                    if domain:
                        return f"https://{domain}"
        except Exception:
            pass

        return None

    def _download_logo(self, domain: str, brand_dir: Path) -> Optional[str]:
        """Download logo from Brandfetch CDN."""
        if not self.brandfetch_client_id:
            return None

        # Extract just the domain from URL
        domain_only = domain.replace("https://", "").replace("http://", "")

        url = f"https://cdn.brandfetch.io/{domain_only}?c={self.brandfetch_client_id}"
        try:
            response = requests.get(url, timeout=10)
            if response.ok:
                content_type = response.headers.get("content-type", "").lower()

                # Validate content-type is actually an image
                valid_image_types = ["image/png", "image/jpeg", "image/jpg", "image/svg+xml", "image/svg"]
                is_image = any(img_type in content_type for img_type in valid_image_types)
                if not is_image:
                    # Not an image (likely HTML error page)
                    return None

                # Extra safety: check content doesn't start with HTML
                content_start = response.content[:100].lower()
                if b"<!doctype" in content_start or b"<html" in content_start:
                    return None

                # Determine extension
                if "svg" in content_type:
                    ext = "svg"
                elif "jpeg" in content_type or "jpg" in content_type:
                    ext = "jpg"
                else:
                    ext = "png"

                brand_dir.mkdir(parents=True, exist_ok=True)
                logo_path = brand_dir / f"logo.{ext}"
                logo_path.write_bytes(response.content)
                return ext
        except Exception:
            pass

        return None

    def _process_materials(
        self,
        brand_id: str,
        brand_dir: Path,
        materials: list[dict],
        packages_by_material: dict[str, list[dict]],
        dry_run: bool,
    ) -> None:
        """Process all materials for a brand."""
        # Group by material type and filament
        # Structure: {material_type: {filament_id: {color_id: {variant_data, sizes}}}}
        hierarchy: dict[str, dict[str, dict[str, dict]]] = {}

        for material in materials:
            # Skip non-FFF materials
            if material.get("class") != "FFF":
                continue

            material_type = material.get("type", "").upper()
            if not material_type:
                continue

            material_slug = material.get("slug", "")
            name = material.get("name", "")
            tags = material.get("tags", [])
            properties = material.get("properties", {})

            # Parse material name to get filament_id and color_id
            filament_id, color_id = self._parse_material_name(name, material_type, tags)

            if not filament_id or not color_id:
                self.report.parse_warnings.append(f"Could not parse: {name}")
                continue

            # Initialize hierarchy levels
            if material_type not in hierarchy:
                hierarchy[material_type] = {}
            if filament_id not in hierarchy[material_type]:
                hierarchy[material_type][filament_id] = {}

            # Build variant data
            primary_color = material.get("primary_color", {})
            color_rgba = primary_color.get("color_rgba") if primary_color else None
            secondary_colors = material.get("secondary_colors", [])

            # Handle multi-color
            if secondary_colors:
                color_hex = [convert_rgba_to_rgb(c.get("color_rgba")) for c in secondary_colors]
                if color_rgba:
                    color_hex.insert(0, convert_rgba_to_rgb(color_rgba))
            else:
                color_hex = convert_rgba_to_rgb(color_rgba)

            variant_data = {
                "id": color_id,
                "name": self._extract_color_name(name, material_type, tags),
                "color_hex": color_hex,
            }

            # Add traits from tags
            traits = self._map_tags_to_traits(tags)
            if traits:
                variant_data["traits"] = traits

            # Build filament data (if not already set)
            if color_id not in hierarchy[material_type][filament_id]:
                filament_data = {
                    "id": filament_id,
                    "name": self._extract_filament_name(name, material_type, tags),
                    "density": properties.get("density", DENSITY_DEFAULTS.get(material_type, 1.24)),
                    "diameter_tolerance": 0.02,  # Default
                }

                # Add temperature data: from OPT if available, otherwise from defaults
                temp_fields = [
                    "min_print_temperature",
                    "max_print_temperature",
                    "min_bed_temperature",
                    "max_bed_temperature",
                    "preheat_temperature",
                    "chamber_temperature",
                    "min_chamber_temperature",
                    "max_chamber_temperature",
                ]

                if "min_print_temperature" in properties:
                    # Use OPT temperatures
                    for field in temp_fields:
                        if field in properties:
                            filament_data[field] = properties[field]
                else:
                    # Apply defaults based on material type
                    temp_defaults = TEMPERATURE_DEFAULTS.get(material_type, {})
                    if temp_defaults:
                        for field, value in temp_defaults.items():
                            filament_data[field] = value
                    else:
                        # No defaults available - track as missing
                        self.report.missing_temperatures.append(f"{brand_id}/{material_type}/{filament_id}")

                hierarchy[material_type][filament_id][color_id] = {
                    "filament": filament_data,
                    "variant": variant_data,
                    "sizes": [],
                }
            else:
                hierarchy[material_type][filament_id][color_id]["variant"] = variant_data

            # Add sizes from packages
            material_packages = packages_by_material.get(material_slug, [])
            for pkg in material_packages:
                size_data = {
                    "filament_weight": pkg.get("nominal_netto_full_weight", 1000),
                    "diameter": microns_to_mm(pkg.get("filament_diameter", 1750)),
                }
                if pkg.get("gtin"):
                    size_data["gtin"] = str(pkg["gtin"])

                hierarchy[material_type][filament_id][color_id]["sizes"].append(size_data)

            self.report.materials_imported += 1

        # Write the hierarchy to disk
        self._write_hierarchy(brand_dir, hierarchy, dry_run)

    def _parse_material_name(
        self, name: str, material_type: str, tags: list[str]
    ) -> tuple[str, str]:
        """Parse OPT material name into (filament_id, color_id)."""
        # Strategy 1: Comma-separated (3D Fuel style)
        if ", " in name:
            parts = name.split(", ", 1)
            product_line = parts[0].strip()
            color = parts[1].strip() if len(parts) > 1 else "default"
            return (slugify(product_line), slugify(color))

        # Strategy 2: Use type + tags to identify product line
        name_lower = name.lower()
        type_lower = material_type.lower()

        # Build filament name from type + modifiers
        modifiers = []
        if "silk" in tags:
            modifiers.append("silk")
        if "matte" in tags:
            modifiers.append("matte")
        if "high_speed" in tags or "high speed" in name_lower:
            modifiers.append("high_speed")
        if "glow_in_the_dark" in tags or "glow" in name_lower:
            modifiers.append("glow")
        if "contains_carbon_fiber" in tags or "cf" in name_lower or "carbon fiber" in name_lower:
            modifiers.append("cf")
        if "contains_glass_fiber" in tags or "gf" in name_lower or "glass fiber" in name_lower:
            modifiers.append("gf")

        if modifiers:
            filament_id = "_".join(modifiers) + "_" + type_lower
        else:
            filament_id = type_lower

        # Extract color by removing known parts from name
        color = name
        # Remove material type mentions and common prefixes
        remove_patterns = [
            material_type,
            type_lower,
            r"\baf\b",
            r"\bpro\b",
            r"\btough\b",
            r"\bsilk\b",
            r"\bmatte\b",
            r"\bhigh\s*speed\b",
            r"\bpla\+?\b",
            r"\bpetg\b",
            r"\babs\b",
            r"\basa\b",
            r"\btpu\b",
            r"\bpctg\b",
        ]
        for pattern in remove_patterns:
            color = re.sub(pattern, "", color, flags=re.IGNORECASE)

        color = color.strip(" ,-+")
        color_id = slugify(color) if color else "default"

        return (filament_id, color_id)

    def _extract_color_name(self, name: str, material_type: str, tags: list[str]) -> str:
        """Extract human-readable color name from material name."""
        # If comma-separated, take second part
        if ", " in name:
            parts = name.split(", ", 1)
            return parts[1].strip() if len(parts) > 1 else "Default"

        # Remove material type and common prefixes
        color = name
        remove_patterns = [
            material_type,
            r"\baf\b",
            r"\bpro\b",
            r"\btough\b",
            r"\bsilk\b",
            r"\bmatte\b",
            r"\bhigh\s*speed\b",
        ]
        for pattern in remove_patterns:
            color = re.sub(pattern, "", color, flags=re.IGNORECASE)

        color = color.strip(" ,-+")
        return color if color else "Default"

    def _extract_filament_name(self, name: str, material_type: str, tags: list[str]) -> str:
        """Extract human-readable filament name from material name."""
        # If comma-separated, take first part
        if ", " in name:
            return name.split(", ", 1)[0].strip()

        # Build from type + modifiers
        parts = [material_type]
        if "silk" in tags:
            parts.insert(0, "Silk")
        if "matte" in tags:
            parts.insert(0, "Matte")
        if "contains_carbon_fiber" in tags:
            parts.append("CF")
        if "contains_glass_fiber" in tags:
            parts.append("GF")

        return " ".join(parts)

    def _map_tags_to_traits(self, tags: list[str]) -> dict[str, bool]:
        """Convert OPT tags to internal traits dict."""
        traits: dict[str, bool] = {}
        for tag in tags:
            if tag in TAG_TO_TRAIT_MAP:
                traits[TAG_TO_TRAIT_MAP[tag]] = True
        return traits

    def _write_hierarchy(
        self,
        brand_dir: Path,
        hierarchy: dict[str, dict[str, dict[str, dict]]],
        dry_run: bool,
    ) -> None:
        """Write the material hierarchy to disk."""
        for material_type, filaments in hierarchy.items():
            material_dir = brand_dir / material_type

            if not dry_run:
                material_dir.mkdir(parents=True, exist_ok=True)

                # Write material.json
                material_json = material_dir / "material.json"
                if not material_json.exists():
                    self._save_json(material_json, {"material": material_type})

            for filament_id, colors in filaments.items():
                filament_dir = material_dir / filament_id

                # Get filament data from first color (they share filament data)
                first_color_data = next(iter(colors.values()))
                filament_data = first_color_data.get("filament", {})

                if not dry_run:
                    filament_dir.mkdir(parents=True, exist_ok=True)

                    # Write filament.json (merge with existing)
                    filament_json = filament_dir / "filament.json"
                    if filament_json.exists():
                        try:
                            with open(filament_json, encoding="utf-8") as f:
                                existing = json.load(f)
                            filament_data = self._merge_data(existing, filament_data)
                        except Exception:
                            pass
                    self._save_json(filament_json, filament_data)

                self.report.filaments_created += 1

                for color_id, color_data in colors.items():
                    variant_dir = filament_dir / color_id
                    variant_data = color_data.get("variant", {})
                    sizes_data = color_data.get("sizes", [])

                    if not dry_run:
                        variant_dir.mkdir(parents=True, exist_ok=True)

                        # Write variant.json (merge with existing)
                        variant_json = variant_dir / "variant.json"
                        if variant_json.exists():
                            try:
                                with open(variant_json, encoding="utf-8") as f:
                                    existing = json.load(f)
                                variant_data = self._merge_data(existing, variant_data)
                            except Exception:
                                pass
                        self._save_json(variant_json, variant_data)

                        # Write sizes.json (merge with existing, create default if needed)
                        sizes_json = variant_dir / "sizes.json"
                        if sizes_json.exists():
                            try:
                                with open(sizes_json, encoding="utf-8") as f:
                                    existing_sizes = json.load(f)
                                if sizes_data:
                                    # Merge sizes by weight+diameter
                                    existing_keys = {
                                        (s.get("filament_weight"), s.get("diameter"))
                                        for s in existing_sizes
                                    }
                                    for size in sizes_data:
                                        key = (size.get("filament_weight"), size.get("diameter"))
                                        if key not in existing_keys:
                                            existing_sizes.append(size)
                                sizes_data = existing_sizes
                            except Exception:
                                pass

                        # Create default size if no sizes data
                        if not sizes_data:
                            sizes_data = [{"filament_weight": 1000, "diameter": 1.75}]

                        self._save_json(sizes_json, sizes_data)
                        self.report.sizes_created += len(sizes_data)

                    self.report.variants_created += 1

    def _save_json(self, path: Path, data: Any) -> None:
        """Save data to JSON file with consistent formatting."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

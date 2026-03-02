"""
Data models for the Open Filament Database.

These dataclasses are aligned with the JSON schemas and represent
the canonical structure of the database entities.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DocumentType(str, Enum):
    """Document types."""

    TDS = "tds"  # Technical Data Sheet
    SDS = "sds"  # Safety Data Sheet


@dataclass
class SlicerSettings:
    """Slicer-specific settings."""

    profile_name: str
    overrides: dict[str, Any] | None = None
    id: str | None = None
    generic_id: str | None = None


@dataclass
class GenericSlicerSettings:
    """Generic slicer temperature settings."""

    first_layer_bed_temp: int | None = None
    first_layer_nozzle_temp: int | None = None
    bed_temp: int | None = None
    nozzle_temp: int | None = None


@dataclass
class AllSlicerSettings:
    """Container for all slicer settings."""

    prusaslicer: SlicerSettings | None = None
    bambustudio: SlicerSettings | None = None
    orcaslicer: SlicerSettings | None = None
    cura: SlicerSettings | None = None
    superslicer: SlicerSettings | None = None
    elegooslicer: SlicerSettings | None = None
    generic: GenericSlicerSettings | None = None


@dataclass
class ColorStandards:
    """Color standard references."""

    ral: str | None = None
    ncs: str | None = None
    pantone: str | None = None
    bs: str | None = None
    munsell: str | None = None


@dataclass
class VariantTraits:
    """Variant traits/properties."""

    translucent: bool = False
    glow: bool = False
    matte: bool = False
    recycled: bool = False
    recyclable: bool = False
    biodegradable: bool = False


# =============================================================================
# Core Entities
# =============================================================================


@dataclass
class Brand:
    """Filament manufacturer/brand."""

    id: str
    name: str
    slug: str
    directory_name: str  # Original directory name (internal use only)
    website: str
    logo: str
    origin: str  # ISO 3166-1 alpha-2 country code


@dataclass
class Material:
    """Material type configuration at brand level."""

    id: str
    brand_id: str
    material: str  # Material type (PLA, PETG, etc.)
    slug: str  # URL-safe slug (derived from material type)
    default_max_dry_temperature: int | None = None
    default_slicer_settings: AllSlicerSettings | None = None


@dataclass
class Filament:
    """Filament product line (e.g., Prusament PLA)."""

    id: str
    brand_id: str
    material_id: str
    name: str
    slug: str
    material: str  # Material type for convenience
    density: float
    diameter_tolerance: float
    max_dry_temperature: int | None = None
    data_sheet_url: str | None = None
    safety_sheet_url: str | None = None
    discontinued: bool = False
    slicer_settings: AllSlicerSettings | None = None


@dataclass
class Variant:
    """Color/finish variant of a filament."""

    id: str
    filament_id: str
    slug: str
    color_name: str
    color_hex: str  # Primary hex color
    hex_variants: list[str] | None = None  # Alternative hex codes (NFC, etc.)
    color_standards: ColorStandards | None = None
    traits: VariantTraits | None = None
    discontinued: bool = False


@dataclass
class Size:
    """Individual spool size/SKU."""

    id: str
    variant_id: str
    filament_weight: int  # Weight in grams
    diameter: float  # Filament diameter in mm
    empty_spool_weight: int | None = None
    spool_core_diameter: float | None = None
    gtin: str | None = None  # GTIN-12 or GTIN-13
    article_number: str | None = None
    barcode_identifier: str | None = None
    nfc_identifier: str | None = None
    qr_identifier: str | None = None
    discontinued: bool = False


@dataclass
class Store:
    """Retail store."""

    id: str
    name: str
    slug: str
    directory_name: str  # Original directory name (internal use only)
    storefront_url: str
    logo: str
    ships_from: list[str]  # ISO 3166-1 alpha-2 country codes
    ships_to: list[str]  # ISO 3166-1 alpha-2 country codes


@dataclass
class PurchaseLink:
    """Purchase link for a specific size at a store."""

    id: str
    size_id: str
    store_id: str
    url: str
    spool_refill: bool = False
    ships_from: list[str] | None = None  # Override store ships_from
    ships_to: list[str] | None = None  # Override store ships_to


# =============================================================================
# Database Container
# =============================================================================


@dataclass
class Database:
    """Container for all database entities."""

    brands: list[Brand] = field(default_factory=list)
    materials: list[Material] = field(default_factory=list)
    filaments: list[Filament] = field(default_factory=list)
    variants: list[Variant] = field(default_factory=list)
    sizes: list[Size] = field(default_factory=list)
    stores: list[Store] = field(default_factory=list)
    purchase_links: list[PurchaseLink] = field(default_factory=list)

    def get_brand(self, brand_id: str) -> Brand | None:
        """Get brand by ID."""
        for brand in self.brands:
            if brand.id == brand_id:
                return brand
        return None

    def get_material(self, material_id: str) -> Material | None:
        """Get material by ID."""
        for material in self.materials:
            if material.id == material_id:
                return material
        return None

    def get_filament(self, filament_id: str) -> Filament | None:
        """Get filament by ID."""
        for filament in self.filaments:
            if filament.id == filament_id:
                return filament
        return None

    def get_variant(self, variant_id: str) -> Variant | None:
        """Get variant by ID."""
        for variant in self.variants:
            if variant.id == variant_id:
                return variant
        return None

    def get_size(self, size_id: str) -> Size | None:
        """Get size by ID."""
        for size in self.sizes:
            if size.id == size_id:
                return size
        return None

    def get_store(self, store_id: str) -> Store | None:
        """Get store by ID."""
        for store in self.stores:
            if store.id == store_id:
                return store
        return None

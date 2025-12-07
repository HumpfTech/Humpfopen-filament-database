"""
SQLite exporter that creates a relational database with proper schema.
"""

import json
import lzma
import sqlite3
from dataclasses import is_dataclass
from pathlib import Path
from typing import Any

from ..models import Database


def entity_to_dict(entity: Any) -> dict:
    """Convert a dataclass entity to a dictionary, handling nested dataclasses."""
    if entity is None:
        return None
    if is_dataclass(entity) and not isinstance(entity, type):
        result = {}
        for field_name in entity.__dataclass_fields__:
            value = getattr(entity, field_name)
            if value is not None:
                if is_dataclass(value) and not isinstance(value, type):
                    result[field_name] = entity_to_dict(value)
                elif isinstance(value, list):
                    result[field_name] = [
                        entity_to_dict(v) if is_dataclass(v) and not isinstance(v, type) else v
                        for v in value
                    ]
                else:
                    result[field_name] = value
        return result
    return entity


# SQLite schema DDL aligned with the data models
SCHEMA_DDL = """
PRAGMA foreign_keys = ON;

-- Metadata table
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Brand table
CREATE TABLE IF NOT EXISTS brand (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    website TEXT NOT NULL,
    logo TEXT NOT NULL,
    origin TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_brand_name ON brand(name);

-- Material table (at brand level)
CREATE TABLE IF NOT EXISTS material (
    id TEXT PRIMARY KEY,
    brand_id TEXT NOT NULL REFERENCES brand(id) ON DELETE CASCADE,
    material TEXT NOT NULL,
    default_max_dry_temperature INTEGER,
    default_slicer_settings TEXT  -- JSON
);
CREATE INDEX IF NOT EXISTS ix_material_brand ON material(brand_id);
CREATE INDEX IF NOT EXISTS ix_material_type ON material(material);

-- Filament table
CREATE TABLE IF NOT EXISTS filament (
    id TEXT PRIMARY KEY,
    brand_id TEXT NOT NULL REFERENCES brand(id) ON DELETE CASCADE,
    material_id TEXT NOT NULL REFERENCES material(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    material TEXT NOT NULL,
    density REAL NOT NULL,
    diameter_tolerance REAL NOT NULL,
    max_dry_temperature INTEGER,
    data_sheet_url TEXT,
    safety_sheet_url TEXT,
    discontinued INTEGER NOT NULL DEFAULT 0,
    slicer_ids TEXT,  -- JSON
    slicer_settings TEXT  -- JSON
);
CREATE INDEX IF NOT EXISTS ix_filament_brand ON filament(brand_id);
CREATE INDEX IF NOT EXISTS ix_filament_material ON filament(material_id);
CREATE INDEX IF NOT EXISTS ix_filament_slug ON filament(slug);

-- Variant table
CREATE TABLE IF NOT EXISTS variant (
    id TEXT PRIMARY KEY,
    filament_id TEXT NOT NULL REFERENCES filament(id) ON DELETE CASCADE,
    slug TEXT NOT NULL,
    color_name TEXT NOT NULL,
    color_hex TEXT NOT NULL,
    hex_variants TEXT,  -- JSON array
    color_standards TEXT,  -- JSON
    traits TEXT,  -- JSON
    discontinued INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_variant_filament ON variant(filament_id);
CREATE INDEX IF NOT EXISTS ix_variant_slug ON variant(slug);
CREATE INDEX IF NOT EXISTS ix_variant_color ON variant(color_name);

-- Size table (spool size/SKU)
CREATE TABLE IF NOT EXISTS size (
    id TEXT PRIMARY KEY,
    variant_id TEXT NOT NULL REFERENCES variant(id) ON DELETE CASCADE,
    filament_weight INTEGER NOT NULL,
    diameter REAL NOT NULL,
    empty_spool_weight INTEGER,
    spool_core_diameter REAL,
    gtin TEXT,
    article_number TEXT,
    barcode_identifier TEXT,
    nfc_identifier TEXT,
    qr_identifier TEXT,
    discontinued INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_size_variant ON size(variant_id);
CREATE INDEX IF NOT EXISTS ix_size_gtin ON size(gtin);
CREATE INDEX IF NOT EXISTS ix_size_weight ON size(filament_weight);

-- Store table
CREATE TABLE IF NOT EXISTS store (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    storefront_url TEXT NOT NULL,
    logo TEXT NOT NULL,
    ships_from TEXT NOT NULL,  -- JSON array
    ships_to TEXT NOT NULL  -- JSON array
);
CREATE INDEX IF NOT EXISTS ix_store_name ON store(name);

-- Purchase link table
CREATE TABLE IF NOT EXISTS purchase_link (
    id TEXT PRIMARY KEY,
    size_id TEXT NOT NULL REFERENCES size(id) ON DELETE CASCADE,
    store_id TEXT NOT NULL REFERENCES store(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    spool_refill INTEGER NOT NULL DEFAULT 0,
    ships_from TEXT,  -- JSON array (override)
    ships_to TEXT  -- JSON array (override)
);
CREATE INDEX IF NOT EXISTS ix_purchase_link_size ON purchase_link(size_id);
CREATE INDEX IF NOT EXISTS ix_purchase_link_store ON purchase_link(store_id);

-- Useful views
CREATE VIEW IF NOT EXISTS v_full_variant AS
SELECT
    v.id AS variant_id,
    v.color_name,
    v.color_hex,
    v.slug AS variant_slug,
    f.id AS filament_id,
    f.name AS filament_name,
    f.slug AS filament_slug,
    f.material,
    f.density,
    f.diameter_tolerance,
    b.id AS brand_id,
    b.name AS brand_name,
    b.slug AS brand_slug
FROM variant v
JOIN filament f ON v.filament_id = f.id
JOIN brand b ON f.brand_id = b.id;

CREATE VIEW IF NOT EXISTS v_full_size AS
SELECT
    s.id AS size_id,
    s.filament_weight,
    s.diameter,
    s.gtin,
    v.id AS variant_id,
    v.color_name,
    v.color_hex,
    f.id AS filament_id,
    f.name AS filament_name,
    f.material,
    b.id AS brand_id,
    b.name AS brand_name
FROM size s
JOIN variant v ON s.variant_id = v.id
JOIN filament f ON v.filament_id = f.id
JOIN brand b ON f.brand_id = b.id;

CREATE VIEW IF NOT EXISTS v_purchase_offers AS
SELECT
    pl.id AS purchase_link_id,
    pl.url,
    pl.spool_refill,
    st.id AS store_id,
    st.name AS store_name,
    st.storefront_url,
    COALESCE(pl.ships_from, st.ships_from) AS ships_from,
    COALESCE(pl.ships_to, st.ships_to) AS ships_to,
    s.id AS size_id,
    s.filament_weight,
    s.diameter,
    s.gtin,
    v.color_name,
    v.color_hex,
    f.name AS filament_name,
    f.material,
    b.name AS brand_name
FROM purchase_link pl
JOIN store st ON pl.store_id = st.id
JOIN size s ON pl.size_id = s.id
JOIN variant v ON s.variant_id = v.id
JOIN filament f ON v.filament_id = f.id
JOIN brand b ON f.brand_id = b.id;
"""


def export_sqlite(db: Database, output_dir: str, version: str, generated_at: str):
    """Export database to SQLite format."""
    output_path = Path(output_dir) / "sqlite"
    output_path.mkdir(parents=True, exist_ok=True)

    db_path = output_path / "filaments.db"

    # Remove existing database
    if db_path.exists():
        db_path.unlink()

    # Create database
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create schema
    cursor.executescript(SCHEMA_DDL)

    # Insert metadata
    cursor.execute("INSERT INTO meta (key, value) VALUES (?, ?)", ("version", version))
    cursor.execute("INSERT INTO meta (key, value) VALUES (?, ?)", ("generated_at", generated_at))

    # Insert brands
    for brand in db.brands:
        cursor.execute(
            "INSERT INTO brand (id, name, slug, website, logo, origin) VALUES (?, ?, ?, ?, ?, ?)",
            (brand.id, brand.name, brand.slug, brand.website, brand.logo, brand.origin)
        )

    # Insert materials
    for material in db.materials:
        slicer_settings = None
        if material.default_slicer_settings:
            slicer_settings = json.dumps(entity_to_dict(material.default_slicer_settings))

        cursor.execute(
            """INSERT INTO material (id, brand_id, material, default_max_dry_temperature, default_slicer_settings)
               VALUES (?, ?, ?, ?, ?)""",
            (material.id, material.brand_id, material.material,
             material.default_max_dry_temperature, slicer_settings)
        )

    # Insert filaments
    for filament in db.filaments:
        slicer_ids = None
        if filament.slicer_ids:
            slicer_ids = json.dumps(entity_to_dict(filament.slicer_ids))

        slicer_settings = None
        if filament.slicer_settings:
            slicer_settings = json.dumps(entity_to_dict(filament.slicer_settings))

        cursor.execute(
            """INSERT INTO filament (id, brand_id, material_id, name, slug, material, density,
               diameter_tolerance, max_dry_temperature, data_sheet_url, safety_sheet_url,
               discontinued, slicer_ids, slicer_settings)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (filament.id, filament.brand_id, filament.material_id, filament.name,
             filament.slug, filament.material, filament.density, filament.diameter_tolerance,
             filament.max_dry_temperature, filament.data_sheet_url, filament.safety_sheet_url,
             1 if filament.discontinued else 0, slicer_ids, slicer_settings)
        )

    # Insert variants
    for variant in db.variants:
        hex_variants = None
        if variant.hex_variants:
            hex_variants = json.dumps(variant.hex_variants)

        color_standards = None
        if variant.color_standards:
            color_standards = json.dumps(entity_to_dict(variant.color_standards))

        traits = None
        if variant.traits:
            traits = json.dumps(entity_to_dict(variant.traits))

        cursor.execute(
            """INSERT INTO variant (id, filament_id, slug, color_name, color_hex, hex_variants,
               color_standards, traits, discontinued)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (variant.id, variant.filament_id, variant.slug, variant.color_name,
             variant.color_hex, hex_variants, color_standards, traits,
             1 if variant.discontinued else 0)
        )

    # Insert sizes
    for size in db.sizes:
        cursor.execute(
            """INSERT INTO size (id, variant_id, filament_weight, diameter, empty_spool_weight,
               spool_core_diameter, gtin, article_number, barcode_identifier, nfc_identifier,
               qr_identifier, discontinued)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (size.id, size.variant_id, size.filament_weight, size.diameter,
             size.empty_spool_weight, size.spool_core_diameter, size.gtin,
             size.article_number, size.barcode_identifier, size.nfc_identifier,
             size.qr_identifier, 1 if size.discontinued else 0)
        )

    # Insert stores
    for store in db.stores:
        cursor.execute(
            """INSERT INTO store (id, name, slug, storefront_url, logo, ships_from, ships_to)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (store.id, store.name, store.slug, store.storefront_url, store.logo,
             json.dumps(store.ships_from), json.dumps(store.ships_to))
        )

    # Insert purchase links
    for pl in db.purchase_links:
        ships_from = None
        if pl.ships_from:
            ships_from = json.dumps(pl.ships_from)

        ships_to = None
        if pl.ships_to:
            ships_to = json.dumps(pl.ships_to)

        cursor.execute(
            """INSERT INTO purchase_link (id, size_id, store_id, url, spool_refill, ships_from, ships_to)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (pl.id, pl.size_id, pl.store_id, pl.url, 1 if pl.spool_refill else 0,
             ships_from, ships_to)
        )

    conn.commit()
    conn.close()
    print(f"  Written: {db_path}")

    # Create compressed version
    db_xz_path = output_path / "filaments.db.xz"
    with open(db_path, 'rb') as f_in:
        with lzma.open(db_xz_path, 'wb') as f_out:
            f_out.write(f_in.read())
    print(f"  Written: {db_xz_path}")

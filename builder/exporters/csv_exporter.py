"""
CSV exporter that creates normalized CSV files.
"""

import csv
import json
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


def list_to_json(value) -> str:
    """Convert a list to JSON string or return empty string."""
    if value is None:
        return ""
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def dict_to_json(value) -> str:
    """Convert a dict/dataclass to JSON string or return empty string."""
    if value is None:
        return ""
    if is_dataclass(value) and not isinstance(value, type):
        return json.dumps(entity_to_dict(value), ensure_ascii=False)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def export_csv(db: Database, output_dir: str, version: str, generated_at: str):
    """Export database to CSV files."""
    output_path = Path(output_dir) / "csv"
    output_path.mkdir(parents=True, exist_ok=True)

    # Export brands
    brands_path = output_path / "brands.csv"
    with open(brands_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'name', 'slug', 'website', 'logo', 'origin'])
        for brand in db.brands:
            writer.writerow([
                brand.id, brand.name, brand.slug, brand.website, brand.logo, brand.origin
            ])
    print(f"  Written: {brands_path}")

    # Export materials
    materials_path = output_path / "materials.csv"
    with open(materials_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'brand_id', 'material', 'default_max_dry_temperature', 'default_slicer_settings'])
        for material in db.materials:
            writer.writerow([
                material.id, material.brand_id, material.material,
                material.default_max_dry_temperature or '',
                dict_to_json(material.default_slicer_settings)
            ])
    print(f"  Written: {materials_path}")

    # Export filaments
    filaments_path = output_path / "filaments.csv"
    with open(filaments_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'id', 'brand_id', 'material_id', 'name', 'slug', 'material',
            'density', 'diameter_tolerance', 'max_dry_temperature',
            'data_sheet_url', 'safety_sheet_url', 'discontinued',
            'slicer_ids', 'slicer_settings'
        ])
        for filament in db.filaments:
            writer.writerow([
                filament.id, filament.brand_id, filament.material_id,
                filament.name, filament.slug, filament.material,
                filament.density, filament.diameter_tolerance,
                filament.max_dry_temperature or '',
                filament.data_sheet_url or '', filament.safety_sheet_url or '',
                '1' if filament.discontinued else '0',
                dict_to_json(filament.slicer_ids),
                dict_to_json(filament.slicer_settings)
            ])
    print(f"  Written: {filaments_path}")

    # Export variants
    variants_path = output_path / "variants.csv"
    with open(variants_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'id', 'filament_id', 'slug', 'color_name', 'color_hex',
            'hex_variants', 'color_standards', 'traits', 'discontinued'
        ])
        for variant in db.variants:
            writer.writerow([
                variant.id, variant.filament_id, variant.slug,
                variant.color_name, variant.color_hex,
                list_to_json(variant.hex_variants),
                dict_to_json(variant.color_standards),
                dict_to_json(variant.traits),
                '1' if variant.discontinued else '0'
            ])
    print(f"  Written: {variants_path}")

    # Export sizes
    sizes_path = output_path / "sizes.csv"
    with open(sizes_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'id', 'variant_id', 'filament_weight', 'diameter',
            'empty_spool_weight', 'spool_core_diameter', 'gtin',
            'article_number', 'barcode_identifier', 'nfc_identifier',
            'qr_identifier', 'discontinued'
        ])
        for size in db.sizes:
            writer.writerow([
                size.id, size.variant_id, size.filament_weight, size.diameter,
                size.empty_spool_weight or '', size.spool_core_diameter or '',
                size.gtin or '', size.article_number or '',
                size.barcode_identifier or '', size.nfc_identifier or '',
                size.qr_identifier or '', '1' if size.discontinued else '0'
            ])
    print(f"  Written: {sizes_path}")

    # Export stores
    stores_path = output_path / "stores.csv"
    with open(stores_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'name', 'slug', 'storefront_url', 'logo', 'ships_from', 'ships_to'])
        for store in db.stores:
            writer.writerow([
                store.id, store.name, store.slug, store.storefront_url, store.logo,
                list_to_json(store.ships_from), list_to_json(store.ships_to)
            ])
    print(f"  Written: {stores_path}")

    # Export purchase links
    purchase_links_path = output_path / "purchase_links.csv"
    with open(purchase_links_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'size_id', 'store_id', 'url', 'spool_refill', 'ships_from', 'ships_to'])
        for pl in db.purchase_links:
            writer.writerow([
                pl.id, pl.size_id, pl.store_id, pl.url,
                '1' if pl.spool_refill else '0',
                list_to_json(pl.ships_from), list_to_json(pl.ships_to)
            ])
    print(f"  Written: {purchase_links_path}")

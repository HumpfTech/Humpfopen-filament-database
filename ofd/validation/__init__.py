"""
OFD Validation Module.

Thin wrapper around the ofd_validator Rust package, providing a
ValidationOrchestrator class that preserves the existing API while
delegating all validation logic to ofd-validator.
"""

import json
import sys
from pathlib import Path
from typing import Optional

from ofd_validator import (
    ValidationLevel,
    ValidationError,
    ValidationResult,
    validate_all as _validate_all,
    validate_json_files as _validate_json_files,
    validate_logo_files as _validate_logo_files,
    validate_folder_names as _validate_folder_names,
    validate_store_ids as _validate_store_ids,
    validate_gtin_ean as _validate_gtin_ean,
    validate_required_files as _validate_required_files,
)


class ValidationOrchestrator:
    """Orchestrates all validation tasks using the ofd-validator Rust package."""

    def __init__(self, data_dir: Path = Path("./data"),
                 stores_dir: Path = Path("./stores"),
                 max_workers: Optional[int] = None,
                 progress_mode: bool = False):
        self.data_dir = str(data_dir)
        self.stores_dir = str(stores_dir)
        self.progress_mode = progress_mode

    def emit_progress(self, stage: str, percent: int, message: str = '') -> None:
        """Emit progress event as JSON to stdout for SSE streaming."""
        if self.progress_mode and hasattr(sys.stdout, 'isatty') and not sys.stdout.isatty():
            print(json.dumps({
                'type': 'progress',
                'stage': stage,
                'percent': percent,
                'message': message
            }), flush=True)

    def validate_json_files(self) -> ValidationResult:
        """Validate all JSON files against schemas."""
        return _validate_json_files(self.data_dir, self.stores_dir)

    def validate_logo_files(self) -> ValidationResult:
        """Validate all logo files."""
        return _validate_logo_files(self.data_dir, self.stores_dir)

    def validate_folder_names(self) -> ValidationResult:
        """Validate all folder names."""
        return _validate_folder_names(self.data_dir, self.stores_dir)

    def validate_store_ids(self) -> ValidationResult:
        """Validate store IDs."""
        return _validate_store_ids(self.data_dir, self.stores_dir)

    def validate_gtin(self) -> ValidationResult:
        """Validate GTIN/EAN rules."""
        return _validate_gtin_ean(self.data_dir)

    def validate_all(self) -> ValidationResult:
        """Run all validations."""
        self.emit_progress('validation', 0, 'Running all validations...')
        result = _validate_all(self.data_dir, self.stores_dir)
        self.emit_progress('validation', 100, 'Validation complete')
        return result


__all__ = [
    'ValidationLevel',
    'ValidationError',
    'ValidationResult',
    'ValidationOrchestrator',
]

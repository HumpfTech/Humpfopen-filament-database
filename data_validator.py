import json
import re
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any

from PIL import Image
from jsonschema import validate, ValidationError as JsonSchemaValidationError


# -------------------------
# Configuration & Constants
# -------------------------

class ValidationLevel(Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"


ILLEGAL_CHARACTERS = [
    "#", "%", "&", "{", "}", "\\", "<", ">", "*", "?",
    "/", "$", "!", "'", '"', ":", "@", "+", "`", "|", "="
]

LOGO_MIN_SIZE = 100
LOGO_MAX_SIZE = 400
SNAKE_CASE_PATTERN = re.compile(r'^[a-z0-9]+(?:_[a-z0-9]+)*$')


# -------------------------
# Data Classes
# -------------------------

@dataclass
class ValidationError:
    """Represents a single validation error."""
    level: ValidationLevel
    category: str
    message: str
    path: Optional[Path] = None

    def __str__(self) -> str:
        path_str = f" [{self.path}]" if self.path else ""
        return f"{self.level.value} - {self.category}: {self.message}{path_str}"


@dataclass
class ValidationResult:
    """Aggregates validation errors."""
    errors: List[ValidationError] = field(default_factory=list)

    def add_error(self, error: ValidationError) -> None:
        self.errors.append(error)

    def merge(self, other: 'ValidationResult') -> None:
        self.errors.extend(other.errors)

    @property
    def is_valid(self) -> bool:
        return not any(e.level == ValidationLevel.ERROR for e in self.errors)

    @property
    def error_count(self) -> int:
        return len([e for e in self.errors if e.level == ValidationLevel.ERROR])

    @property
    def warning_count(self) -> int:
        return len([e for e in self.errors if e.level == ValidationLevel.WARNING])


# -------------------------
# Utility Functions
# -------------------------

def load_json(path: Path) -> Optional[Dict[str, Any]]:
    """Load JSON from file with error handling."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return None


def cleanse_folder_name(name: str) -> str:
    """Clean folder name by replacing slashes and stripping whitespace."""
    return name.replace("/", " ").strip()


# -------------------------
# Schema Cache
# -------------------------

class SchemaCache:
    """Lazy-loading cache for JSON schemas."""

    def __init__(self):
        self._schemas: Dict[str, Dict] = {}
        self._schema_paths = {
            'store':    'schemas/store_schema.json',
            'brand':    'schemas/brand_schema.json',
            'material': 'schemas/material_schema.json',
            'filament': 'schemas/filament_schema.json',
            'variant':  'schemas/variant_schema.json',
            'sizes':    'schemas/sizes_schema.json',
        }

    def get(self, schema_name: str) -> Optional[Dict]:
        """Get schema by name, loading if necessary."""
        if schema_name not in self._schemas:
            path = Path(self._schema_paths.get(schema_name, ''))
            if path.exists():
                self._schemas[schema_name] = load_json(path)
        return self._schemas.get(schema_name)


# -------------------------
# Validators
# -------------------------

class BaseValidator:
    """Base class for all validators."""

    def __init__(self, schema_cache: Optional[SchemaCache] = None):
        self.schema_cache = schema_cache or SchemaCache()

    def validate(self, *args, **kwargs) -> ValidationResult:
        """Override in subclasses."""
        raise NotImplementedError


class JsonValidator(BaseValidator):
    """Validates JSON files against schemas."""

    def validate_json_file(self, json_path: Path, schema_name: str) -> ValidationResult:
        """Validate a single JSON file against a schema."""
        result = ValidationResult()

        data = load_json(json_path)
        if data is None:
            result.add_error(ValidationError(
                level=ValidationLevel.ERROR,
                category="JSON",
                message=f"Failed to load JSON file",
                path=json_path
            ))
            return result

        schema = self.schema_cache.get(schema_name)
        if schema is None:
            result.add_error(ValidationError(
                level=ValidationLevel.ERROR,
                category="JSON",
                message=f"Schema '{schema_name}' not found",
                path=json_path
            ))
            return result

        try:
            validate(data, schema)
        except JsonSchemaValidationError as e:
            result.add_error(ValidationError(
                level=ValidationLevel.ERROR,
                category="JSON",
                message=f"Schema validation failed: {e.message} at {e.json_path}",
                path=json_path
            ))

        return result


class LogoValidator(BaseValidator):
    """Validates logo files (dimensions and naming)."""

    def validate_logo_file(self, logo_path: Path,
                           logo_name: str = None) -> ValidationResult:
        """Validate logo dimensions and naming convention."""
        result = ValidationResult()

        # Check if logo name contains "/" (should be just filename)
        if logo_name and "/" in logo_name:
            result.add_error(ValidationError(
                level=ValidationLevel.ERROR,
                category="Logo",
                message=f"Logo path '{logo_name}' contains '/' - only use filename",
                path=logo_path.parent
            ))

        if not logo_path.exists():
            result.add_error(ValidationError(
                level=ValidationLevel.ERROR,
                category="Logo",
                message="Logo file not found",
                path=logo_path
            ))
            return result

        # Validate naming convention
        name = logo_path.name
        if not name.endswith('.svg'):
            name_without_ext = logo_path.stem
            if not SNAKE_CASE_PATTERN.fullmatch(name_without_ext):
                result.add_error(ValidationError(
                    level=ValidationLevel.ERROR,
                    category="Logo",
                    message=f"Logo name '{name}' must follow lowercase snake_case (e.g., sunlu.png or proteor_print.png)",
                    path=logo_path
                ))

        # Validate dimensions for non-SVG files
        if not name.endswith('.svg'):
            try:
                with Image.open(logo_path) as img:
                    width, height = img.size

                    if width != height:
                        result.add_error(ValidationError(
                            level=ValidationLevel.ERROR,
                            category="Logo",
                            message=f"Logo must be square (width={width}, height={height})",
                            path=logo_path
                        ))

                    if width < LOGO_MIN_SIZE or height < LOGO_MIN_SIZE:
                        result.add_error(ValidationError(
                            level=ValidationLevel.ERROR,
                            category="Logo",
                            message=f"Logo dimensions too small (minimum {LOGO_MIN_SIZE}x{LOGO_MIN_SIZE})",
                            path=logo_path
                        ))

                    if width > LOGO_MAX_SIZE or height > LOGO_MAX_SIZE:
                        result.add_error(ValidationError(
                            level=ValidationLevel.ERROR,
                            category="Logo",
                            message=f"Logo dimensions too large (maximum {LOGO_MAX_SIZE}x{LOGO_MAX_SIZE})",
                            path=logo_path
                        ))
            except Exception as e:
                result.add_error(ValidationError(
                    level=ValidationLevel.ERROR,
                    category="Logo",
                    message=f"Failed to read image: {str(e)}",
                    path=logo_path
                ))

        return result


class FolderNameValidator(BaseValidator):
    """Validates that folder names match JSON content."""

    def validate_folder_name(self, folder_path: Path, json_file: str,
                             json_key: str) -> ValidationResult:
        """Validate that folder name matches the value in the JSON file."""
        result = ValidationResult()

        json_path = folder_path / json_file
        if not json_path.exists():
            result.add_error(ValidationError(
                level=ValidationLevel.ERROR,
                category="Folder",
                message=f"Missing {json_file}",
                path=folder_path
            ))
            return result

        data = load_json(json_path)
        if data is None:
            return result

        expected_name = cleanse_folder_name(data.get(json_key, ""))
        actual_name = folder_path.name

        if actual_name != expected_name:
            # Check if it's due to illegal characters
            has_illegal_chars = any(
                char in expected_name for char in ILLEGAL_CHARACTERS)

            if not has_illegal_chars:
                result.add_error(ValidationError(
                    level=ValidationLevel.ERROR,
                    category="Folder",
                    message=f"Folder name '{actual_name}' does not match '{json_key}' value '{expected_name}' in {json_file}",
                    path=folder_path
                ))

        return result


class StoreIdValidator(BaseValidator):
    """Validates that store IDs in purchase links are valid."""

    def validate_store_ids(self, data_dir: Path, stores_dir: Path) -> ValidationResult:
        """Validate all store IDs referenced in sizes.json files."""
        result = ValidationResult()

        # Collect valid store IDs
        valid_store_ids = set()
        for store_file in stores_dir.glob("*/store.json"):
            data = load_json(store_file)
            if data and "id" in data:
                valid_store_ids.add(data["id"])

        # Validate references in sizes.json files
        for sizes_file in data_dir.glob("**/sizes.json"):
            sizes_data = load_json(sizes_file)
            if not sizes_data:
                continue

            for size_idx, size in enumerate(sizes_data):
                for link_idx, link in enumerate(size.get("purchase_links", [])):
                    store_id = link.get("store_id")
                    if store_id and store_id not in valid_store_ids:
                        result.add_error(ValidationError(
                            level=ValidationLevel.ERROR,
                            category="StoreID",
                            message=f"Invalid store_id '{store_id}' at $[{size_idx}].purchase_links[{link_idx}]",
                            path=sizes_file
                        ))

        return result


class MissingFileValidator(BaseValidator):
    """Validates that required JSON files exist."""

    def validate_required_files(self, data_dir: Path,
                                stores_dir: Path) -> ValidationResult:
        """Check for missing required JSON files."""
        result = ValidationResult()

        # Check brand directories
        for brand_dir in data_dir.iterdir():
            if not brand_dir.is_dir():
                continue

            brand_file = brand_dir / "brand.json"
            if not brand_file.exists():
                result.add_error(ValidationError(
                    level=ValidationLevel.ERROR,
                    category="Missing File",
                    message="Missing brand.json",
                    path=brand_dir
                ))

            # Check material directories
            for material_dir in brand_dir.iterdir():
                if not material_dir.is_dir():
                    continue

                material_file = material_dir / "material.json"
                if not material_file.exists():
                    result.add_error(ValidationError(
                        level=ValidationLevel.ERROR,
                        category="Missing File",
                        message="Missing material.json",
                        path=material_dir
                    ))

                # Check filament directories
                for filament_dir in material_dir.iterdir():
                    if not filament_dir.is_dir():
                        continue

                    filament_file = filament_dir / "filament.json"
                    if not filament_file.exists():
                        result.add_error(ValidationError(
                            level=ValidationLevel.ERROR,
                            category="Missing File",
                            message="Missing filament.json",
                            path=filament_dir
                        ))

                    # Check variant directories
                    for variant_dir in filament_dir.iterdir():
                        if not variant_dir.is_dir():
                            continue

                        variant_file = variant_dir / "variant.json"
                        if not variant_file.exists():
                            result.add_error(ValidationError(
                                level=ValidationLevel.ERROR,
                                category="Missing File",
                                message="Missing variant.json",
                                path=variant_dir
                            ))

                        sizes_file = variant_dir / "sizes.json"
                        if not sizes_file.exists():
                            result.add_error(ValidationError(
                                level=ValidationLevel.ERROR,
                                category="Missing File",
                                message="Missing sizes.json",
                                path=variant_dir
                            ))

        # Check store directories
        for store_dir in stores_dir.iterdir():
            if not store_dir.is_dir():
                continue

            store_file = store_dir / "store.json"
            if not store_file.exists():
                result.add_error(ValidationError(
                    level=ValidationLevel.ERROR,
                    category="Missing File",
                    message="Missing store.json",
                    path=store_dir
                ))

        return result


# -------------------------
# Validation Tasks
# -------------------------

@dataclass
class ValidationTask:
    """Represents a validation task to be executed."""
    task_type: str
    name: str
    path: Path
    extra_data: Optional[Dict[str, Any]] = None


def _execute_validation_task(task: ValidationTask) -> ValidationResult:
    """
    Worker function to execute a validation task.
    This is a module-level function so it can be pickled for multiprocessing.
    """
    schema_cache = SchemaCache()
    extra = task.extra_data or {}

    if task.task_type == 'json':
        validator = JsonValidator(schema_cache)
        schema_name = extra.get('schema_name', '')
        return validator.validate_json_file(task.path, schema_name)

    elif task.task_type == 'logo':
        validator = LogoValidator(schema_cache)
        logo_name = extra.get('logo_name')
        return validator.validate_logo_file(task.path, logo_name)

    elif task.task_type == 'folder':
        validator = FolderNameValidator(schema_cache)
        json_file = extra.get('json_file', '')
        json_key = extra.get('json_key', '')
        return validator.validate_folder_name(task.path, json_file, json_key)

    else:
        result = ValidationResult()
        result.add_error(ValidationError(
            level=ValidationLevel.ERROR,
            category="System",
            message=f"Unknown task type: {task.task_type}"
        ))
        return result


def collect_json_validation_tasks(data_dir: Path, stores_dir: Path) -> List[
    ValidationTask]:
    """Collect all JSON validation tasks."""
    tasks = []

    # Brand validation tasks
    for brand_dir in data_dir.iterdir():
        if not brand_dir.is_dir():
            continue

        brand_file = brand_dir / "brand.json"
        if brand_file.exists():
            tasks.append(ValidationTask(
                task_type='json',
                name=f"Brand JSON: {brand_dir.name}",
                path=brand_file,
                extra_data={'schema_name': 'brand'}
            ))

        # Material validation tasks
        for material_dir in brand_dir.iterdir():
            if not material_dir.is_dir():
                continue

            material_file = material_dir / "material.json"
            if material_file.exists():
                tasks.append(ValidationTask(
                    task_type='json',
                    name=f"Material JSON: {material_dir.name}",
                    path=material_file,
                    extra_data={'schema_name': 'material'}
                ))

            # Filament validation tasks
            for filament_dir in material_dir.iterdir():
                if not filament_dir.is_dir():
                    continue

                filament_file = filament_dir / "filament.json"
                if filament_file.exists():
                    tasks.append(ValidationTask(
                        task_type='json',
                        name=f"Filament JSON: {filament_dir.name}",
                        path=filament_file,
                        extra_data={'schema_name': 'filament'}
                    ))

                # Variant validation tasks
                for variant_dir in filament_dir.iterdir():
                    if not variant_dir.is_dir():
                        continue

                    variant_file = variant_dir / "variant.json"
                    if variant_file.exists():
                        tasks.append(ValidationTask(
                            task_type='json',
                            name=f"Variant JSON: {variant_dir.name}",
                            path=variant_file,
                            extra_data={'schema_name': 'variant'}
                        ))

                    sizes_file = variant_dir / "sizes.json"
                    if sizes_file.exists():
                        tasks.append(ValidationTask(
                            task_type='json',
                            name=f"Sizes JSON: {variant_dir.name}",
                            path=sizes_file,
                            extra_data={'schema_name': 'sizes'}
                        ))

    # Store validation tasks
    for store_dir in stores_dir.iterdir():
        if not store_dir.is_dir():
            continue

        store_file = store_dir / "store.json"
        if store_file.exists():
            tasks.append(ValidationTask(
                task_type='json',
                name=f"Store JSON: {store_dir.name}",
                path=store_file,
                extra_data={'schema_name': 'store'}
            ))

    return tasks


def collect_logo_validation_tasks(data_dir: Path, stores_dir: Path) -> List[
    ValidationTask]:
    """Collect all logo validation tasks."""
    tasks = []

    # Brand logos
    for brand_dir in data_dir.iterdir():
        if not brand_dir.is_dir():
            continue

        brand_file = brand_dir / "brand.json"
        if brand_file.exists():
            data = load_json(brand_file)
            if data and "logo" in data:
                logo_name = data["logo"]
                logo_path = brand_dir / logo_name
                tasks.append(ValidationTask(
                    task_type='logo',
                    name=f"Brand Logo: {brand_dir.name}",
                    path=logo_path,
                    extra_data={'logo_name': logo_name}
                ))

    # Store logos
    for store_dir in stores_dir.iterdir():
        if not store_dir.is_dir():
            continue

        store_file = store_dir / "store.json"
        if store_file.exists():
            data = load_json(store_file)
            if data and "logo" in data:
                logo_name = data["logo"]
                logo_path = store_dir / logo_name
                tasks.append(ValidationTask(
                    task_type='logo',
                    name=f"Store Logo: {store_dir.name}",
                    path=logo_path,
                    extra_data={'logo_name': logo_name}
                ))

    return tasks


def collect_folder_validation_tasks(data_dir: Path, stores_dir: Path) -> List[
    ValidationTask]:
    """Collect all folder name validation tasks."""
    tasks = []

    # Brand folders
    for brand_dir in data_dir.iterdir():
        if not brand_dir.is_dir():
            continue

        tasks.append(ValidationTask(
            task_type='folder',
            name=f"Brand Folder: {brand_dir.name}",
            path=brand_dir,
            extra_data={'json_file': 'brand.json', 'json_key': 'brand'}
        ))

        # Material folders
        for material_dir in brand_dir.iterdir():
            if not material_dir.is_dir():
                continue

            tasks.append(ValidationTask(
                task_type='folder',
                name=f"Material Folder: {material_dir.name}",
                path=material_dir,
                extra_data={'json_file': 'material.json', 'json_key': 'material'}
            ))

            # Filament folders
            for filament_dir in material_dir.iterdir():
                if not filament_dir.is_dir():
                    continue

                tasks.append(ValidationTask(
                    task_type='folder',
                    name=f"Filament Folder: {filament_dir.name}",
                    path=filament_dir,
                    extra_data={'json_file': 'filament.json', 'json_key': 'name'}
                ))

                # Variant folders
                for variant_dir in filament_dir.iterdir():
                    if not variant_dir.is_dir():
                        continue

                    tasks.append(ValidationTask(
                        task_type='folder',
                        name=f"Variant Folder: {variant_dir.name}",
                        path=variant_dir,
                        extra_data={'json_file': 'variant.json',
                                    'json_key':  'color_name'}
                    ))

    # Store folders
    for store_dir in stores_dir.iterdir():
        if not store_dir.is_dir():
            continue

        tasks.append(ValidationTask(
            task_type='folder',
            name=f"Store Folder: {store_dir.name}",
            path=store_dir,
            extra_data={'json_file': 'store.json', 'json_key': 'id'}
        ))

    return tasks


# -------------------------
# Main Validation Orchestrator
# -------------------------

class ValidationOrchestrator:
    """Orchestrates all validation tasks with multiprocessing support."""

    def __init__(self, data_dir: Path = Path("./data"),
                 stores_dir: Path = Path("./stores"),
                 max_workers: Optional[int] = None):
        self.data_dir = data_dir
        self.stores_dir = stores_dir
        self.max_workers = max_workers
        self.schema_cache = SchemaCache()

    def run_tasks_parallel(self, tasks: List[ValidationTask]) -> ValidationResult:
        """Run validation tasks in parallel using process pool."""
        result = ValidationResult()

        if not tasks:
            return result

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_task = {executor.submit(_execute_validation_task, task): task for
                              task in tasks}

            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    task_result = future.result()
                    result.merge(task_result)
                except Exception as e:
                    result.add_error(ValidationError(
                        level=ValidationLevel.ERROR,
                        category="System",
                        message=f"Task '{task.name}' failed with exception: {str(e)}"
                    ))

        return result

    def validate_json_files(self) -> ValidationResult:
        """Validate all JSON files against schemas."""
        print("Collecting JSON validation tasks...")
        tasks = collect_json_validation_tasks(self.data_dir, self.stores_dir)
        print(f"Running {len(tasks)} JSON validation tasks...")
        return self.run_tasks_parallel(tasks)

    def validate_logo_files(self) -> ValidationResult:
        """Validate all logo files."""
        print("Collecting logo validation tasks...")
        tasks = collect_logo_validation_tasks(self.data_dir, self.stores_dir)
        print(f"Running {len(tasks)} logo validation tasks...")
        return self.run_tasks_parallel(tasks)

    def validate_folder_names(self) -> ValidationResult:
        """Validate all folder names."""
        print("Collecting folder name validation tasks...")
        tasks = collect_folder_validation_tasks(self.data_dir, self.stores_dir)
        print(f"Running {len(tasks)} folder name validation tasks...")
        return self.run_tasks_parallel(tasks)

    def validate_store_ids(self) -> ValidationResult:
        """Validate store IDs."""
        print("Validating store IDs...")
        validator = StoreIdValidator(self.schema_cache)
        return validator.validate_store_ids(self.data_dir, self.stores_dir)

    def validate_all(self) -> ValidationResult:
        """Run all validations."""
        result = ValidationResult()

        # Check for missing files first
        print("Checking for missing required files...")
        validator = MissingFileValidator(self.schema_cache)
        result.merge(validator.validate_required_files(self.data_dir, self.stores_dir))

        result.merge(self.validate_json_files())
        result.merge(self.validate_logo_files())
        result.merge(self.validate_folder_names())
        result.merge(self.validate_store_ids())

        return result


# -------------------------
# CLI Entry Point
# -------------------------

def main():
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Validate filament data structure")
    parser.add_argument("--json-files", action="store_true", help="Validate JSON files")
    parser.add_argument("--logo-files", action="store_true", help="Validate logo files")
    parser.add_argument("--folder-names", action="store_true",
                        help="Validate folder names")
    parser.add_argument("--store-ids", action="store_true", help="Validate store IDs")

    args = parser.parse_args()

    orchestrator = ValidationOrchestrator(max_workers=os.cpu_count())
    result = ValidationResult()

    # Run requested validations
    if not any(vars(args).values()):
        print("No args passed, validating all")
        result = orchestrator.validate_all()
    else:
        if args.json_files:
            result.merge(orchestrator.validate_json_files())
        if args.logo_files:
            result.merge(orchestrator.validate_logo_files())
        if args.folder_names:
            result.merge(orchestrator.validate_folder_names())
        if args.store_ids:
            result.merge(orchestrator.validate_store_ids())

    # Print results
    if result.errors:
        # Group errors by category
        errors_by_category: Dict[str, List[ValidationError]] = {}
        for error in result.errors:
            if error.category not in errors_by_category:
                errors_by_category[error.category] = []
            errors_by_category[error.category].append(error)

        # Print errors grouped by category
        for category, errors in sorted(errors_by_category.items()):
            print(f"\n{category} ({len(errors)}):")
            print("-" * 80)
            for error in errors:
                print(f"  {error}")

        print(
            f"\nValidation failed: {result.error_count} errors, {result.warning_count} warnings")
        exit(1)
    else:
        print("All validations passed!")
        exit(0)


if __name__ == '__main__':
    main()

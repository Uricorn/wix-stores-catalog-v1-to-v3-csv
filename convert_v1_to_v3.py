#!/usr/bin/env python3
"""Convert Wix Stores Catalog V1 product CSV export to V3 import format."""

from __future__ import annotations

import argparse
import csv
import itertools
import re
import sys
from collections import Counter
from pathlib import Path

V3_COLUMNS = [
    "handle",
    "fieldType",
    "name",
    "visible",
    "plainDescription",
    "categorySlugs",
    "primaryCategorySlug",
    "media",
    "mediaAltText",
    "ribbon",
    "brand",
    "price",
    "strikethroughPrice",
    "cost",
    "inventory",
    "preOrderEnabled",
    "preOrderMessage",
    "preOrderLimit",
    "sku",
    "barcode",
    "weight",
    "baseUnit",
    "baseUnitMeasurement",
    "totalUnits",
    "totalUnitsMeasurement",
    "productOptionName1",
    "productOptionType1",
    "productOptionChoices1",
    "productOptionName2",
    "productOptionType2",
    "productOptionChoices2",
    "productOptionName3",
    "productOptionType3",
    "productOptionChoices3",
    "productOptionName4",
    "productOptionType4",
    "productOptionChoices4",
    "productOptionName5",
    "productOptionType5",
    "productOptionChoices5",
    "productOptionName6",
    "productOptionType6",
    "productOptionChoices6",
    "modifierName1",
    "modifierType1",
    "modifierCharLimit1",
    "modifierMandatory1",
    "modifierDescription1",
    "modifierName2",
    "modifierType2",
    "modifierCharLimit2",
    "modifierMandatory2",
    "modifierDescription2",
    "modifierName3",
    "modifierType3",
    "modifierCharLimit3",
    "modifierMandatory3",
    "modifierDescription3",
    "modifierName4",
    "modifierType4",
    "modifierCharLimit4",
    "modifierMandatory4",
    "modifierDescription4",
    "modifierName5",
    "modifierType5",
    "modifierCharLimit5",
    "modifierMandatory5",
    "modifierDescription5",
    "modifierName6",
    "modifierType6",
    "modifierCharLimit6",
    "modifierMandatory6",
    "modifierDescription6",
    "modifierName7",
    "modifierType7",
    "modifierCharLimit7",
    "modifierMandatory7",
    "modifierDescription7",
    "modifierName8",
    "modifierType8",
    "modifierCharLimit8",
    "modifierMandatory8",
    "modifierDescription8",
    "modifierName9",
    "modifierType9",
    "modifierCharLimit9",
    "modifierMandatory9",
    "modifierDescription9",
    "modifierName10",
    "modifierType10",
    "modifierCharLimit10",
    "modifierMandatory10",
    "modifierDescription10",
]

OPTION_TYPE_MAP = {
    "DROP_DOWN": "TEXT_CHOICES",
    "drop_down": "TEXT_CHOICES",
    "TEXT": "TEXT_CHOICES",
    "COLOR": "SWATCH_CHOICES",
    "color": "SWATCH_CHOICES",
    "SWATCH": "SWATCH_CHOICES",
}

INVENTORY_MAP = {
    "InStock": "IN_STOCK",
    "OutOfStock": "OUT_OF_STOCK",
    "In Stock": "IN_STOCK",
    "Out of Stock": "OUT_OF_STOCK",
}

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FIELD_LIMITS = {
    "name": 80,
    "ribbon": 30,
    "brand": 50,
    "sku": 40,
    "plainDescription": 16000,
}


def empty_row() -> dict[str, str]:
    return {col: "" for col in V3_COLUMNS}


def truncate(value: str, limit: int) -> str:
    value = (value or "").strip()
    if len(value) <= limit:
        return value
    return value[:limit]


def to_handle(handle_id: str) -> str:
    handle_id = handle_id.strip()
    if handle_id.lower().startswith("product_"):
        return "Product_" + handle_id.split("_", 1)[1]
    if handle_id.lower().startswith("product-"):
        return "Product_" + handle_id.split("-", 1)[1]
    return handle_id


def to_wix_bool(value: str, *, default: bool = True) -> str:
    text = (value or "").strip().lower()
    if text in {"true", "1", "yes"}:
        return "TRUE"
    if text in {"false", "0", "no"}:
        return "FALSE"
    return "TRUE" if default else "FALSE"


def slugify_category(name: str) -> str:
    slug = name.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def category_values(row: dict[str, str], mode: str) -> tuple[str, str]:
    collections = [c.strip() for c in (row.get("collection") or "").split(";") if c.strip()]
    if mode == "skip" or not collections:
        return "", ""
    slugs = [slugify_category(c) for c in collections]
    # Never populate primaryCategorySlug: Wix CSV import passes it as category.id on
    # createCategory, which the Categories API rejects. Secondary slugs work.
    return ";".join(slugs), ""


def convert_option_type(v1_type: str) -> str:
    return OPTION_TYPE_MAP.get(v1_type.strip(), v1_type.strip() or "TEXT_CHOICES")


def convert_inventory(v1_inventory: str) -> str:
    value = (v1_inventory or "").strip()
    if not value:
        return "IN_STOCK"
    if value.isdigit():
        return value
    return INVENTORY_MAP.get(value, value.upper().replace(" ", "_"))


def convert_prices(price_raw: str, discount_mode: str, discount_value_raw: str) -> tuple[str, str]:
    if not price_raw:
        return "", ""
    price = float(price_raw)
    discount_value = float(discount_value_raw or 0)
    if discount_value <= 0:
        return format_price(price), ""

    if discount_mode.upper() == "AMOUNT":
        actual = max(price - discount_value, 0)
    else:
        actual = price * (1 - discount_value / 100)

    return format_price(actual), format_price(price)


def format_price(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def append_additional_info(description: str, row: dict[str, str]) -> str:
    sections: list[str] = []
    for i in range(1, 7):
        title = (row.get(f"additionalInfoTitle{i}") or "").strip()
        body = (row.get(f"additionalInfoDescription{i}") or "").strip()
        if not title and not body:
            continue
        if title and body:
            sections.append(f"<h3>{title}</h3>{body}")
        elif title:
            sections.append(f"<h3>{title}</h3>")
        else:
            sections.append(body)
    if not sections:
        return description
    merged = (description or "").strip()
    if merged:
        merged += "".join(sections)
    else:
        merged = "".join(sections)
    return truncate(merged, FIELD_LIMITS["plainDescription"])


def get_options(row: dict[str, str]) -> list[dict[str, str]]:
    options: list[dict[str, str]] = []
    for i in range(1, 7):
        name = (row.get(f"productOptionName{i}") or "").strip()
        if not name:
            continue
        option_type = convert_option_type(row.get(f"productOptionType{i}", ""))
        choices_raw = (row.get(f"productOptionDescription{i}") or "").strip()
        choices = [c.strip() for c in choices_raw.split(";") if c.strip()]
        options.append({"name": truncate(name, 50), "type": option_type, "choices": choices})
    return options


def get_modifiers(row: dict[str, str]) -> list[dict[str, str]]:
    modifiers: list[dict[str, str]] = []
    for i in range(1, 3):
        name = (row.get(f"customTextField{i}") or "").strip()
        if not name:
            continue
        modifiers.append(
            {
                "name": truncate(name, 50),
                "type": "FREE_TEXT",
                "char_limit": (row.get(f"customTextCharLimit{i}") or "").strip(),
                "mandatory": to_wix_bool(row.get(f"customTextMandatory{i}", ""), default=False),
            }
        )
    return modifiers


def set_options_on_row(target: dict[str, str], options: list[dict[str, str]], *, selected: list[str] | None = None) -> None:
    for idx, option in enumerate(options[:6], start=1):
        target[f"productOptionName{idx}"] = option["name"]
        target[f"productOptionType{idx}"] = option["type"]
        if selected is not None:
            target[f"productOptionChoices{idx}"] = selected[idx - 1]
        else:
            target[f"productOptionChoices{idx}"] = ";".join(option["choices"])


def set_modifiers_on_row(target: dict[str, str], modifiers: list[dict[str, str]]) -> None:
    for idx, modifier in enumerate(modifiers[:10], start=1):
        target[f"modifierName{idx}"] = modifier["name"]
        target[f"modifierType{idx}"] = modifier["type"]
        target[f"modifierCharLimit{idx}"] = modifier["char_limit"]
        target[f"modifierMandatory{idx}"] = modifier["mandatory"]


def convert_product_row(row: dict[str, str], *, category_mode: str = "slugs") -> list[dict[str, str]]:
    handle = to_handle(row.get("handleId", ""))
    options = get_options(row)
    modifiers = get_modifiers(row)
    actual_price, compare_at = convert_prices(
        row.get("price", ""),
        row.get("discountMode", ""),
        row.get("discountValue", ""),
    )
    category_slugs, primary_category = category_values(row, category_mode)
    visible = to_wix_bool(row.get("visible", ""), default=True)

    product = empty_row()
    product.update(
        {
            "handle": handle,
            "fieldType": "PRODUCT",
            "name": truncate(row.get("name", ""), FIELD_LIMITS["name"]),
            "visible": visible,
            "plainDescription": append_additional_info(row.get("description", ""), row),
            "categorySlugs": category_slugs,
            "primaryCategorySlug": primary_category,
            "ribbon": truncate(row.get("ribbon", ""), FIELD_LIMITS["ribbon"]),
            "brand": truncate(row.get("brand", ""), FIELD_LIMITS["brand"]),
            "preOrderEnabled": "FALSE",
        }
    )
    set_modifiers_on_row(product, modifiers)

    output_rows: list[dict[str, str]] = [product]

    if options:
        set_options_on_row(product, options)
        for combo in itertools.product(*(opt["choices"] for opt in options)):
            variant = empty_row()
            variant.update(
                {
                    "handle": handle,
                    "fieldType": "VARIANT",
                    "name": "",
                    "visible": visible,
                    "price": actual_price,
                    "strikethroughPrice": compare_at,
                    "cost": row.get("cost", ""),
                    "inventory": convert_inventory(row.get("inventory", "")),
                    "preOrderEnabled": "FALSE",
                    "sku": truncate(row.get("sku", ""), FIELD_LIMITS["sku"]),
                    "weight": row.get("weight", ""),
                }
            )
            set_options_on_row(variant, options, selected=list(combo))
            output_rows.append(variant)
    else:
        product.update(
            {
                "price": actual_price,
                "strikethroughPrice": compare_at,
                "cost": row.get("cost", ""),
                "inventory": convert_inventory(row.get("inventory", "")),
                "sku": truncate(row.get("sku", ""), FIELD_LIMITS["sku"]),
                "weight": row.get("weight", ""),
            }
        )

    images = [img.strip() for img in (row.get("productImageUrl") or "").split(";") if img.strip()]
    for image in images:
        media_row = empty_row()
        media_row.update({"handle": handle, "fieldType": "MEDIA", "media": image})
        output_rows.append(media_row)

    return output_rows


def validate_v3_rows(rows: list[dict[str, str]]) -> list[str]:
    issues: list[str] = []
    by_handle: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_handle.setdefault(row["handle"], []).append(row)

    for handle, group in by_handle.items():
        products = [r for r in group if r["fieldType"] == "PRODUCT"]
        if len(products) != 1:
            issues.append(f"{handle}: expected exactly 1 PRODUCT row, found {len(products)}")
            continue

        product = products[0]
        if not product.get("name"):
            issues.append(f"{handle}: PRODUCT row missing name")
        if product.get("primaryCategorySlug", "").strip():
            issues.append(f"{handle}: primaryCategorySlug must be empty for import")
        if product.get("visible") not in {"TRUE", "FALSE"}:
            issues.append(f"{handle}: visible must be TRUE or FALSE")
        if product.get("preOrderEnabled") not in {"TRUE", "FALSE"}:
            issues.append(f"{handle}: preOrderEnabled must be TRUE or FALSE")

        for slug in (product.get("categorySlugs") or "").split(";"):
            slug = slug.strip()
            if slug and not SLUG_RE.match(slug):
                issues.append(f"{handle}: invalid category slug '{slug}'")

        price = product.get("price", "")
        strike = product.get("strikethroughPrice", "")
        if price and strike:
            try:
                if float(strike) <= float(price):
                    issues.append(f"{handle}: strikethroughPrice must be greater than price")
            except ValueError:
                issues.append(f"{handle}: invalid price values")

        media_rows = [r for r in group if r["fieldType"] == "MEDIA"]
        for media in media_rows:
            if not media.get("media"):
                issues.append(f"{handle}: MEDIA row missing media value")

    return issues


def write_category_manifest(v1_rows: list[dict[str, str]], manifest_path: Path) -> None:
    counts: Counter[str] = Counter()
    for row in v1_rows:
        for name in (row.get("collection") or "").split(";"):
            name = name.strip()
            if name:
                counts[name] += 1

    with manifest_path.open("w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(
            outfile,
            fieldnames=["categoryName", "categorySlug", "productCount"],
        )
        writer.writeheader()
        for name, count in counts.most_common():
            writer.writerow(
                {
                    "categoryName": name,
                    "categorySlug": slugify_category(name),
                    "productCount": count,
                }
            )


def convert_file(
    input_path: Path,
    output_path: Path,
    *,
    category_mode: str = "slugs",
    manifest_path: Path | None = None,
    strict: bool = False,
) -> dict[str, int]:
    with input_path.open(newline="", encoding="utf-8-sig") as infile:
        reader = csv.DictReader(infile)
        v1_rows = [row for row in reader if (row.get("fieldType") or "").strip().lower() == "product"]

    if manifest_path is not None:
        write_category_manifest(v1_rows, manifest_path)

    output_rows: list[dict[str, str]] = []
    for row in v1_rows:
        output_rows.extend(convert_product_row(row, category_mode=category_mode))

    issues = validate_v3_rows(output_rows)
    if issues:
        for issue in issues[:20]:
            print(f"warning: {issue}", file=sys.stderr)
        if len(issues) > 20:
            print(f"warning: ...and {len(issues) - 20} more", file=sys.stderr)
        if strict:
            raise SystemExit(f"validation failed with {len(issues)} issue(s)")

    with output_path.open("w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=V3_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(output_rows)

    return {
        "v1_products": len(v1_rows),
        "v3_rows": len(output_rows),
        "products": len({r["handle"] for r in output_rows if r["fieldType"] == "PRODUCT"}),
        "variants": len([r for r in output_rows if r["fieldType"] == "VARIANT"]),
        "media": len([r for r in output_rows if r["fieldType"] == "MEDIA"]),
        "validation_issues": len(issues),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="V1 catalog_products.csv export")
    parser.add_argument("output", type=Path, help="Output V3 CSV path")
    parser.add_argument(
        "--categories",
        choices=("slugs", "skip"),
        default="slugs",
        help="slugs: import-ready category slugs (default); skip: leave categories empty",
    )
    parser.add_argument(
        "--category-manifest",
        type=Path,
        help="Write categoryName/categorySlug/productCount CSV (default: <output>-categories.csv)",
    )
    parser.add_argument(
        "--no-category-manifest",
        action="store_true",
        help="Do not write a category manifest file",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with error if validation finds issues",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"error: input file not found: {args.input}", file=sys.stderr)
        return 1

    manifest_path = None
    if not args.no_category_manifest and args.categories == "slugs":
        manifest_path = args.category_manifest or args.output.with_name(f"{args.output.stem}-categories.csv")

    stats = convert_file(
        args.input,
        args.output,
        category_mode=args.categories,
        manifest_path=manifest_path,
        strict=args.strict,
    )
    print(
        "Converted {v1_products} V1 products -> {products} V3 products "
        "({v3_rows} total rows: {variants} variants, {media} media)".format(**stats)
    )
    if stats["validation_issues"]:
        print(f"Validation issues: {stats['validation_issues']}", file=sys.stderr)
    print(f"Wrote {args.output}")
    if manifest_path is not None:
        print(f"Wrote {manifest_path}")
    return 1 if stats["validation_issues"] and args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())

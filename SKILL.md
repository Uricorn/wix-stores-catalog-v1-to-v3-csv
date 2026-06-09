---
name: wix-stores-catalog-v1-to-v3-csv
description: >-
  Converts Wix Stores Catalog V1 product CSV exports into Catalog V3 import
  format. Use when migrating a V1 store catalog to V3, converting
  catalog_products.csv, preparing products for V3 CSV upload, or helping users
  move products between Wix sites on different catalog versions.
---

# Wix Stores Catalog V1 → V3 CSV Migration

Help users export products from a **Catalog V1** Wix site and produce a **Catalog V3** CSV ready for import on their new site.

## When to use

- User has an old V1 site and a new V3 site and wants to move products via CSV
- User provides or mentions `catalog_products.csv` from a V1 export
- User asks about V1→V3 catalog migration, product import template, or field mapping

## First-try import (default)

Run the converter with defaults — no flags needed:

```bash
python3 convert_v1_to_v3.py "catalog_products (v1).csv" "catalog_products (v3).csv"
```

Defaults are tuned for first-try success:

1. **`primaryCategorySlug` left empty** — populated values trigger a Wix import bug (~91% failure rate)
2. **`categorySlugs` as URL slugs** — not display names (spaces/`&` fail validation)
3. **Case-sensitive booleans** — `TRUE` / `FALSE` for `visible`, `preOrderEnabled`, modifiers
4. **Field limits enforced** — name 80, ribbon 30, brand 50, sku 40 chars
5. **Category manifest** written alongside output as `<output>-categories.csv`

User imports on V3: Store Products → More Actions → Import.

After import: activate categories on site, set primary categories in dashboard if needed.

## Prerequisites (tell the user)

1. **Export from V1**: Store Products → More Actions → Import → Export Products
2. **Download V3 template** on target site (for column reference only — do not merge headers)
3. **Do not edit column headers** in output

References:
- [Catalog V1 to V3 Migration Guide](https://dev.wix.com/docs/api-reference/business-solutions/stores/catalog-v3/catalog-v1-to-v3-migration-guide)
- [Importing products (Support)](https://support.wix.com/en/article/wix-stores-importing-products-from-another-ecommerce-platform)

## Core structural change

| V1 CSV | V3 CSV |
|--------|--------|
| One `Product` row per product | `PRODUCT` + `VARIANT` + `MEDIA` rows |
| `handleId` | `handle` (`product_abc` → `Product_abc`) |
| `description` | `plainDescription` |
| `collection` | `categorySlugs` (URL slugs, semicolon-separated) |
| `productOptionDescriptionN` | `productOptionChoicesN` |
| `customTextFieldN` | `modifierNameN` + `FREE_TEXT` |

## Key conversion rules

### Pricing

| V1 | V3 |
|----|-----|
| No discount | `price` only |
| Has discount | `price` = discounted, `strikethroughPrice` = original |

### Categories

- Slugify: `Pumps, Motors & Vacuum` → `pumps-motors-vacuum`
- **Never set `primaryCategorySlug`** — Wix import bug
- Fallback: `--categories skip` then assign in dashboard

### Inventory

`InStock` → `IN_STOCK`, `OutOfStock` → `OUT_OF_STOCK`, numeric unchanged

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `id category ID is not allowed` | `primaryCategorySlug` populated | Re-convert with latest script (leaves it empty) |
| `is not a valid url slug` | Display names in `categorySlugs` | Use slugified values |
| Partial categories created | Old import with primary slug bug | Re-import fixed CSV |

Category errors do not block product import — check Store Products first.

## Additional resources

- [reference.md](reference.md) — full column mapping
- [README.md](README.md) — CLI options

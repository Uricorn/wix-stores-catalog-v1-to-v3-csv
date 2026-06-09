# Wix Stores Catalog V1 → V3 CSV Migration

Convert a **Catalog V1** Wix Stores product export into a **Catalog V3** CSV ready for dashboard import.

This was vibe coded and likely contains some mistakes depending on your flow. Only a simple migration was tested - treat this as a proof of concept.

## Quick start

```bash
python3 convert_v1_to_v3.py "catalog_products (v1).csv" "catalog_products (v3).csv"
```

Then on your **V3 site**: Store Products → More Actions → Import → upload the output file.

## What it fixes for first-try success

| Issue | Fix |
|-------|-----|
| `primaryCategorySlug` import bug | Always left **empty** (Wix passes it as `category.id` on create → fails) |
| Collection names vs slugs | `categorySlugs` uses **URL slugs** (`Dry Cleaning Machine Parts` → `dry-cleaning-machine-parts`) |
| Case-sensitive fields | `visible`, `preOrderEnabled`, `modifierMandatory` → `TRUE` / `FALSE` |
| V1 discounts | Mapped to `price` + `strikethroughPrice` |
| V1 row model | Expands to `PRODUCT` + `VARIANT` + `MEDIA` rows |
| Field limits | Truncates name (80), ribbon (30), brand (50), sku (40), description (16000) |

## Options

```bash
# Import-ready output with category slugs + manifest (default)
python3 convert_v1_to_v3.py input.csv output.csv

# Products only — assign categories manually afterward
python3 convert_v1_to_v3.py input.csv output.csv --categories skip

# Fail on validation warnings
python3 convert_v1_to_v3.py input.csv output.csv --strict
```

The converter also writes `output-categories.csv` listing every category name, slug, and product count.

## After import

1. Check Store Products for your products (category errors do not block product import).
2. Go to **Categories** and toggle new categories **Active on site**.
3. Set primary categories in the dashboard if needed (`primaryCategorySlug` is intentionally omitted).

## Cursor skill

Copy `SKILL.md` to `~/.cursor/skills/wix-stores-catalog-v1-to-v3-csv/SKILL.md` for agent-guided migrations.

## References

- [Catalog V1 to V3 Migration Guide](https://dev.wix.com/docs/api-reference/business-solutions/stores/catalog-v3/catalog-v1-to-v3-migration-guide)
- [Importing products (Support)](https://support.wix.com/en/article/wix-stores-importing-products-from-another-ecommerce-platform)

## License

MIT

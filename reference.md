# V1 → V3 CSV Column Reference

## Row model

```
Product (V1 export)                    Product (V3 import)
─────────────────────                  ─────────────────────────────────
1 × Product row                   →    1 × PRODUCT row
                                       0..N × VARIANT rows (if options)
                                       1..N × MEDIA rows (one per image)
```

## Direct field mapping (single-variant / no options)

| V1 column | V3 column | Row type | Notes |
|-----------|-----------|----------|-------|
| `handleId` | `handle` | all | Prefix `product_` → `Product_` |
| `fieldType` (`Product`) | `fieldType` (`PRODUCT`) | PRODUCT | Uppercase in V3 |
| `name` | `name` | PRODUCT | Max 80 chars |
| `description` | `plainDescription` | PRODUCT | HTML preserved, max 16000 chars |
| `visible` | `visible` | PRODUCT, VARIANT | `TRUE` / `FALSE` |
| `collection` | `categorySlugs` | PRODUCT | Slugify to URL-safe slugs, `;` separated |
| (first collection) | `primaryCategorySlug` | PRODUCT | **Always leave empty** |
| `ribbon` | `ribbon` | PRODUCT | Max 30 chars |
| `brand` | `brand` | PRODUCT | Max 50 chars |
| `price` + discount fields | `price` | PRODUCT or VARIANT | See pricing table |
| `price` (when discounted) | `strikethroughPrice` | PRODUCT or VARIANT | Must be > `price` |
| `cost` | `cost` | PRODUCT or VARIANT | |
| `inventory` | `inventory` | PRODUCT or VARIANT | See inventory table |
| `sku` | `sku` | PRODUCT or VARIANT | Max 40 chars |
| `weight` | `weight` | PRODUCT or VARIANT | |
| `productImageUrl` | `media` | MEDIA | Split on `;`, one row each |

Slugify rule: lowercase, replace non-alphanumeric runs with `-`, trim hyphens.

Example: `Pumps, Motors & Vacuum` → `pumps-motors-vacuum`

## Import-safe defaults

| Field | Value | Why |
|-------|-------|-----|
| `primaryCategorySlug` | empty | Wix import bug when populated |
| `categorySlugs` | URL slugs only | Display names fail slug validation |
| `visible` | `TRUE` / `FALSE` | Case-sensitive in import |
| `preOrderEnabled` | `FALSE` | Case-sensitive in import |
| `inventory` | `IN_STOCK` / `OUT_OF_STOCK` / numeric | Case-sensitive status values |

## Pricing conversion

| V1 fields | Result |
|-----------|--------|
| `price=100`, `discountValue=0` | `price=100`, `strikethroughPrice=` |
| `price=100`, `discountMode=PERCENT`, `discountValue=20` | `price=80`, `strikethroughPrice=100` |
| `price=12.11`, `discountMode=PERCENT`, `discountValue=50` | `price=6.05`, `strikethroughPrice=12.11` |
| `price=50`, `discountMode=AMOUNT`, `discountValue=10` | `price=40`, `strikethroughPrice=50` |

## Inventory conversion

| V1 `inventory` | V3 `inventory` |
|----------------|----------------|
| `InStock` | `IN_STOCK` |
| `OutOfStock` | `OUT_OF_STOCK` |
| `42` | `42` |

## Product options (variant-creating)

| V1 column | V3 column | Row |
|-----------|-----------|-----|
| `productOptionNameN` | `productOptionNameN` | PRODUCT (all choices), VARIANT (one choice) |
| `productOptionTypeN` | `productOptionTypeN` | `TEXT_CHOICES` or `SWATCH_CHOICES` |
| `productOptionDescriptionN` | `productOptionChoicesN` | PRODUCT: `Small;Medium;Large`, VARIANT: `Small` |

## Custom text → modifiers

| V1 | V3 |
|----|-----|
| `customTextFieldN` | `modifierNameN` |
| — | `modifierTypeN` = `FREE_TEXT` |
| `customTextCharLimitN` | `modifierCharLimitN` |
| `customTextMandatoryN` | `modifierMandatoryN` (`TRUE` / `FALSE`) |

## Additional info sections

V3 CSV has no info-section columns. Append to `plainDescription` as `<h3>` blocks.

## Official docs

- [Catalog V1 to V3 Migration Guide](https://dev.wix.com/docs/api-reference/business-solutions/stores/catalog-v3/catalog-v1-to-v3-migration-guide)
- [Importing products (Support)](https://support.wix.com/en/article/wix-stores-importing-products-from-another-ecommerce-platform)

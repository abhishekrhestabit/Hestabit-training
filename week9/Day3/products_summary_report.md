# Products CSV Summary Report

This report summarizes the contents of the `products.csv` file.

## Dataset Overview
- **Total Rows:** 500
- **Columns:** 6 (`id`, `name`, `category`, `price`, `ratings`, `discount`)

## Numerical Summary
| Metric | id | price | ratings | discount |
| :--- | :--- | :--- | :--- | :--- |
| **Mean** | 250.50 | 242.53 | 2.90 | 0.00 |
| **Min** | 1.00 | 6.62 | 1.00 | 0.00 |
| **Max** | 500.00 | 498.47 | 5.00 | 0.00 |

## Categorical Breakdown
The dataset contains products across 5 categories:
- **Electronics:** 118
- **Clothing:** 114
- **Toys:** 94
- **Books:** 91
- **Home:** 83

## Notes
- The `discount` column appears to be empty/zero for all entries.
- The `price` ranges significantly from ~6.62 to ~498.47.
- `ratings` are distributed between 1.0 and 5.0, with a mean of 2.9.

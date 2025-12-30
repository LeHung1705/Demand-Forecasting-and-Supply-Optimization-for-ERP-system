from __future__ import annotations

from pathlib import Path

import pandas as pd


def main() -> None:
    backend_dir = Path(__file__).resolve().parent
    original_path = (backend_dir / "app" / "data" / "original_data.csv").resolve()
    products_path = (backend_dir / "app" / "data" / "products.csv").resolve()

    cols = [
        "store_id",
        "product_id",
        "city_id",
        "first_category_id",
        "second_category_id",
        "third_category_id",
        "management_group_id",
    ]

    if not original_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {original_path.as_posix()}")

    df = pd.read_csv(original_path, usecols=cols)
    identity = df.drop_duplicates(subset=["store_id", "product_id"]).reset_index(drop=True)

    products_path.parent.mkdir(parents=True, exist_ok=True)
    identity.to_csv(products_path, index=False)

    print(
        "Extracted products identity",
        {
            "input": original_path.as_posix(),
            "output": products_path.as_posix(),
            "rows_in": int(len(df)),
            "rows_out": int(len(identity)),
            "columns": cols,
        },
    )


if __name__ == "__main__":
    main()
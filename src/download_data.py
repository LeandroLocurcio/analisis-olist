"""
Descarga automatica de los datasets de Olist desde Kaggle.

Descarga dos datasets:
  - olistbr/brazilian-ecommerce  (9 tablas de pedidos)
  - olistbr/marketing-funnel-olist  (leads y closed deals)

Requisitos:
  - Paquete kaggle instalado (`pip install kaggle`)
  - Credenciales de Kaggle en ~/.kaggle/kaggle.json
    (ver README.md, seccion "Setup" para conseguirlas)

Uso:
    python src/download_data.py
"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

# Carpeta destino (relativa a la raiz del repo)
DATA_DIR = Path(__file__).resolve().parents[1] / "data"

# Datasets de Kaggle a descargar
DATASETS = [
    "olistbr/brazilian-ecommerce",
    "olistbr/marketing-funnel-olist",
]


def check_kaggle_credentials() -> None:
    """Chequea que exista el archivo kaggle.json."""
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    if not kaggle_json.exists():
        raise FileNotFoundError(
            "No se encontraron credenciales de Kaggle en ~/.kaggle/kaggle.json.\n"
            "Revisa la seccion 'Setup' del README para el paso a paso."
        )


def download_and_extract(dataset: str, dest: Path) -> None:
    """Descarga un dataset de Kaggle y descomprime los CSVs en dest."""
    # Import diferido para que el error de kaggle no tape el mensaje si falta pip install
    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()

    print(f"[download] {dataset} -> {dest}")
    dest.mkdir(parents=True, exist_ok=True)
    api.dataset_download_files(dataset, path=str(dest), unzip=False, quiet=False)

    # Kaggle guarda el zip con el nombre corto del dataset
    zip_name = dataset.split("/")[-1] + ".zip"
    zip_path = dest / zip_name

    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest)

    zip_path.unlink()
    print(f"[ok] Descomprimido: {dataset}")


def main() -> None:
    check_kaggle_credentials()

    if DATA_DIR.exists() and any(DATA_DIR.glob("*.csv")):
        print(f"Ya hay CSVs en {DATA_DIR}. Borra la carpeta si queres re-descargar.")
        return

    for dataset in DATASETS:
        download_and_extract(dataset, DATA_DIR)

    csvs = sorted(DATA_DIR.glob("*.csv"))
    print(f"\nListo. {len(csvs)} archivos en {DATA_DIR}:")
    for f in csvs:
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  - {f.name}  ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()

from typing import List

INPE_BDC_STAC_URL: str = "https://data.inpe.br/bdc/stac/v1"

COPERNICUS_STAC_URL: str = "https://catalogue.dataspace.copernicus.eu/stac"

SUPPORTED_SOURCES: List[str] = [
    "Sentinel-2",
    "Landsat",
    "FIRMS",
    "INPE",
]

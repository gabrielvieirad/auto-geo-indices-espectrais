import pystac_client
import planetary_computer

catalog = pystac_client.Client.open(
    "https://planetarycomputer.microsoft.com/api/stac/v1",
    modifier=planetary_computer.sign_inplace,
)

search = catalog.search(
    collections=["landsat-c2-l2"],
    bbox=[-60.5, -3.5, -60.0, -3.0],
    datetime="2024-06-01/2024-09-30",
)

items = list(search.items())
print("Total materializado:", len(items))
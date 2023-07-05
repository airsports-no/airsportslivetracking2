import glob
import numpy as np
import cartopy.crs as ccrs
import utm

from PIL import Image
import qrcode

from display.flight_order_and_maps.mbtiles_facade import get_available_maps


def folder_map_name(folder: str) -> str:
    actual_map = folder.split("/")[-1]
    elements = actual_map.split("_")
    return " ".join([item.capitalize() for item in elements])


def get_map_choices() -> list[tuple[str, str]]:
    return [(item["url"].split("/")[-1], item["name"]) for item in get_available_maps()] + [
        ("osm", "OSM"),
        ("fc", "Flight Contest"),
        ("mto", "MapTiler Outdoor"),
        ("cyclosm", "CycleOSM"),
    ]


def qr_code_image(url: str, image_path: str):
    # taking image which user wants
    # in the QR code center
    logo = Image.open(image_path)

    # taking base width
    basewidth = 150

    # adjust image size
    wpercent = basewidth / float(logo.size[0])
    hsize = int((float(logo.size[1]) * float(wpercent)))
    logo = logo.resize((basewidth, hsize), Image.ANTIALIAS)
    QRcode = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
    # addingg URL or text to QRcode
    QRcode.add_data(url)

    # generating QR code
    QRcode.make()

    # taking color name from user
    QRcolor = "black"

    # adding color to QR code
    QRimg = QRcode.make_image(fill_color=QRcolor, back_color="white").convert("RGB")

    # set size of QR code
    pos = ((QRimg.size[0] - logo.size[0]) // 2, (QRimg.size[1] - logo.size[1]) // 2)
    QRimg.paste(logo, pos)

    # save the QR code generated
    return QRimg

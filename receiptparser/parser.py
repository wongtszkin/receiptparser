import os
import io
import codecs
import pytesseract
from PIL import Image
from wand.image import Image as WandImage
from .receipt import Receipt
import numpy as np
import argparse
import cv2
import pytesseract
from pytesseract import Output
from matplotlib import pyplot as plt

# def deskew(image):
#     gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
#     gray = cv2.bitwise_not(gray)
#     thresh = cv2.threshold(gray, 0, 255,
# 	  cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
#     coords = np.column_stack(np.where(thresh > 0))
#     angle = cv2.minAreaRect(coords)[-1]
#     if angle < -45:
#         angle = -(90 + angle)
#     else:
#         angle = -angle
#     (h, w) = image.shape[:2]
#     center = (w // 2, h // 2)
#     M = cv2.getRotationMatrix2D(center, angle, 1.0)
#     rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
#     return rotated


def ocr_image(input_file, language, sharpen=False, timeout=20):
    """
    :param input_file: str
        Path to image to prettify
    :return: str
    """
    with io.BytesIO() as transfer:
        with WandImage(filename=input_file) as img:
            if sharpen:
                img.auto_level()
                img.sharpen(radius=0, sigma=4.0)
                img.contrast()
            img.save(transfer)

        with Image.open(transfer) as img:
            # img = deskew(img)
            return pytesseract.image_to_string(img, lang=language, timeout=20)

def _process_receipt(config, filename, out_dir=None, sharpen=False):
    result = ocr_image(filename, config.language, sharpen=sharpen)
    if out_dir:
        basename = os.path.basename(filename)
        if sharpen:
            basename += '.sharpen'
        out_filename = os.path.join(out_dir, basename+'.txt')
        with codecs.open(out_filename, 'w') as fp:
            fp.write(result)
    else:
        out_filename = None

    return Receipt(config, out_filename or filename, result)

def process_receipt(config, filename, out_dir=None, verbosity=0):
    if filename.endswith('.txt'):
        if verbosity > 0:
            print("Parsing existing OCR result", filename)
        return Receipt.from_file(config, filename)

    if verbosity > 0:
        print("Performing scan on", filename)
    receipt = _process_receipt(config, filename, out_dir)

    # if not receipt.is_complete():
    #     if verbosity > 0:
    #         print("Performing OCR scan with sharpening", filename)
    #     receipt2 = _process_receipt(config, filename, sharpen=True)
    #     receipt.merge(receipt2)

    return receipt


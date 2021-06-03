import re
import codecs
import datetime
import dateutil.parser
from difflib import get_close_matches
import numpy as np
import argparse
import cv2
import pytesseract
from pytesseract import Output
from matplotlib import pyplot as plt
import csv

class Receipt(object):
    def __init__(self, config, filename, raw):
        """
        :type  config: munch.Munch
        :param config: Configuration as returned by config.read_config()
        :type  filename: str|None
        :param filename: Only stored in the object to ease future debugging
        :type  raw: str
        :param raw: Tesseract textual output
        """
        self.config = config
        self.filename = filename
        self.company = None
        self.date = None
        self.postal = None
        self.sum = None
        self.lines = [l.lower() for l in raw.split('\n') if l.strip()]
        self.parse()

    @classmethod
    def from_file(cls, config, filename):
        with codecs.open(filename) as fp:
            return Receipt(config, filename, fp.read())

    def to_dict(self):
        keys = "filename", "company", "date", "postal", "sum"
        return dict((k, v) for (k, v) in self.__dict__.items() if k in keys)

    def for_format_string(self):
        return {
            'filename': self.filename,
            'company': self.company or 'unknown',
            'date': self.date or datetime.date(1970, 1, 1),
            'postal': self.postal or 'unknown',
            'sum': '?' if self.sum is None else self.sum,
        }

    def is_complete(self):
        return not None in self.to_dict().values()

    def merge(self, receipt):
        for k, v in receipt.to_dict().items():
            if getattr(self, k) is None:
                setattr(self, k, v)

    def parse(self):
        """
        :return: void
            Parses obj data
        """

        
        self.company = self.parse_company()
        self.postal = self.parse_postal()
        self.date = self.parse_date()
        self.sum = self.parse_sum()
        #output a new file
        image = cv2.imread(self.filename)
        h, w, _ = image.shape
        print(self.date)
        # GrayImage=cv2.cvtColor(image ,cv2.COLOR_BGR2GRAY)
        # threshold_img = cv2.threshold(GrayImage, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        # dst = cv.fastNlMeansDenoisingColored(image,None,10,10,7,21)
        custom_config = r'--oem 3 --psm 6'
        details = pytesseract.image_to_data(image, output_type=Output.DICT, config=custom_config, lang='eng')

        total_boxes = len(details['text'])
        for sequence_number in range(total_boxes):
            if int(details['conf'][sequence_number]) >25:
                if details['text'][sequence_number]==str(self.date) or details['text'][sequence_number]==self.sum or details['text'][sequence_number]==self.postal:
                    (x, y, w, h) = (details['left'][sequence_number], details['top'][sequence_number], details['width'][sequence_number],  details['height'][sequence_number])
                    threshold_img = cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.imwrite("image_2.png", threshold_img)
        #output a new file

        parse_text = []

        word_list = []

        last_word = ''

        for word in details['text']:

            if word!='':
                word_list.append(word)
                last_word = word

            if (last_word!='' and word == '') or (word==details['text'][-1]):
                parse_text.append(word_list)
                word_list = []
        
        with open('result.txt',  'w', newline="") as file: 
             csv.writer(file, delimiter=" ").writerows(parse_text)

    def fuzzy_find(self, keyword, accuracy=0.6):
        """
        :param keyword: str
            The keyword string to look for
        :param accuracy: float
            Required accuracy for a match of a string with the keyword
        :return: str
            Returns the first line in lines that contains a keyword.
            It runs a fuzzy match if 0 < accuracy < 1.0
        """
        for line in self.lines:
            words = line.split()
            if re.search(r'\b'+keyword+r'\b', line, re.I):
                return line

            matches = get_close_matches(keyword, words, 1, accuracy)
            if matches:
                return line

    def parse_date(self):
        """
        :return: date
            Parses data
        """
        for line in self.lines:
            match = re.search(self.config.formats.date, line, re.I)
            if match:
                date_str = match.group(1).replace(' ', '')
                try:
                    return dateutil.parser.parse(date_str)
                except:
                    continue

    def parse_postal(self):
        """
        :return: str
        """

        for line in self.lines:
            match = re.search(self.config.formats.postal_code, line, re.I)
            if match:
                try:
                    int(match.group(1))
                except ValueError:
                    continue
                return match.group(1)

    def parse_company(self):
        """
        :return: str
        """

        for int_accuracy in range(10, 6, -1):
            accuracy = int_accuracy/10.0
            for company, spellings in self.config.companys.items():
                for spelling in spellings:
                    line = self.fuzzy_find(spelling, accuracy)
                    if line:
                        return company

    def parse_sum(self):
        """
        :return: str
        """
        for sum_key in self.config.sum_keys:
            sum_line = self.fuzzy_find(sum_key, 0.9)
            if sum_line:
                sum_line = sum_line.replace(",", ".")
                sum_float = re.search(self.config.formats.sum, sum_line)
                if sum_float:
                    return sum_float.group(0)

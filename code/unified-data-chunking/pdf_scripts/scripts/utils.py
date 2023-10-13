import os

import pikepdf
from tika import parser

import camelot.io as camelot


def path(directory, name):
    """"
    returns path of document

    @var self.directory [string], directory of pdf
    @var self.name [string], name of pdf
    
    @returns [string]
    """
    return directory + '/' + name + '.pdf'


def decrypt(self):
    """"
    decrypts pdf if encrypted with no password

    @var self.directory [string], directory of pdf
    @var self.name [string], name of pdf
    
    """
    with pikepdf.open(path(self.directory, self.name)) as pdf:
        # try:
        #     tables = camelot.read_pdf(path(self.directory, self.name), pages='1')
        # except:
            # print('FILE DECRYPTED')
        self.name = "{}-decrypted".format(self.name)
        pdf.save(path(self.directory, self.name))


def create_pdf(self, path_pdf, successive_pages):
    """
    create pdf out of successive pages and considers it as main pdf

    @var self.directory [string], directory of pdf
    @var self.name [string], name of pdf  
    @var path_pdf [string], path of pdf
    @var successive_pages [string],'index_first_page, index_pages_in_between, index_last_page'
    """
    if successive_pages != "all":
        successive_pages = successive_pages.split(',')
        with pikepdf.open(path_pdf) as pdf:
            del pdf.pages[:int(successive_pages[0])]
            del pdf.pages[int(successive_pages[-1]) + 1:]
            pdf.save(path(self.directory, "tmp_pdf"))
        self.name = "tmp_pdf"


def delete_pdf(self, path_pdf, successive_pages):
    """
    deletes pdf of create_pdf

    @var self.directory [string], directory of pdf
    @var self.name [string], name of pdf  
    @var path_pdf [string], path of pdf
    @var successive_pages [string],'index_first_page, index_pages_in_between, index_last_page'
    """
    if successive_pages != "all":
        successive_pages = successive_pages.split(',')
        os.remove(path(self.directory, "tmp_pdf"))
        self.name = path_pdf.replace(self.directory, '').replace('/', '')[:-4]


def table_identifier(directory, index_graph, name):
    """
    @var directory [string], directory of pdf
    @var index_graph [int], index of graph
    @var name [string], name of pdf  

    @returns text [string], identifier of table
    """
    try:  # '//' instead of '///'
        return '{}/table{}-{}'.format(directory[1:], index_graph, name)
    except:
        return '{}/table{}-{}'.format(directory, index_graph, name)

#!/usr/bin/env python
# coding: utf-8
# THESE SCRIPTS ARE DEVELOPED IN PDF-INTEGRATION PROJECT
# Main libraries used (maintained)
## https://github.com/pikepdf/pikepdf (for reading or writing PDF) 
## https://github.com/atlanhq/camelot (for tables extraction)
## https://github.com/chrismattmann/tika-python (for text extraction)

# %% IMPORTS

import re
import os
import argparse

import pandas as pd

import camelot.io as camelot
from tika import parser

import rdflib

from .scripts.utils import path, decrypt, create_pdf, delete_pdf
from .scripts.prepare_text import prepare_text
from .scripts.prepare_tables import prepare_tables
from .scripts.clean_text import text_without_df_full, text2paragraphs, sentence_bounding
from .scripts.clean_tables import naive_merge_intra_tables, merge_inter, merge_intra

pd.set_option("display.max_rows", None, "display.max_columns", None)

# %% CLASS PDF

class PDF:

    def __init__(self, path_pdf, pages, flavor, threshold, graph_position):
        """
        clean text and tables (but doesn't save them)

        @var path_pdf [string], path to pdf
        @var pages [string], number of pages of pdf to be scrapped
        @var flavor [string], type of tables in PDF : "lattice" = separation lines of cell written, "stream" = separation lines of cell not written
        @var threshold [int], from 0 to 100 miminum of accuracy of tables to be scrapped
        @var graph_position [boolean], are the graphs' (their uri) position to be put in the text?
        """

        # %% DECRYPT
        self.directory = os.path.dirname(path_pdf)
        self.name = path_pdf.replace(self.directory, '').replace('\\', '')[:-4]
        decrypt(self)
        path_pdf = path(self.directory, self.name)
        # %% SELECT TABLES (CAMELOT)
        # self.tables = camelot.read_pdf(path(self.directory, self.name), pages=pages, flavor=flavor)
        # self.n_tables = len(self.tables)
        self.tables = None
        self.n_tables = 0
        # %% SELECT TEXT (TIKA)
        create_pdf(self, path_pdf, pages)
        parsedPDF = parser.from_file(path(self.directory, self.name))
        self.text = parsedPDF["content"]

        delete_pdf(self, path_pdf, pages)
        # %% PREPARING
        prepare_text(self)
        # prepare_tables(self, threshold)
        # %% CLEANING

        self.text_without_tables(graph_position)

        self.modify_tables_and_text(flavor, graph_position)

    def text_without_tables(self, graph_position):
        """
        takes off the tables part of the text and turns the text into a list of paragraphs

        @var graph_position [boolean], are the graphs' (their uri) position to be put in the text?
        """
        if self.text:
            # %% TEXT WITHOUT TABLES
            text_without_df_full(self, graph_position)
            # %% TEXT SPLIT IN PARAGRAPHS
            text2paragraphs(self)

    def modify_tables_and_text(self, flavor, graph_position):
        """
        clean tables headers and datacell, adapts positions of tables URIs in text
        clean text by joining sentences together

        @var flavor [string], type of tables in PDF : "lattice" = separation lines of cell written, "stream" = separation lines of cell not written
        @var graph_position [boolean], are the graphs' (their uri) position to be put in the text?
        """
        # if self.tables:
        #     naive_merge_intra_tables(self, flavor)
        #     merge_inter(self, graph_position)
        #     merge_intra(self, flavor)
        if self.text:
            self.text = [word if isinstance(word, rdflib.term.URIRef) else re.sub('( )+', ' ', word) for word in
                         self.text]  # deleting long white spaces in lines
            self.text = sentence_bounding(self.text)  # uniting separated sentences

    # def save_text(self):
    #     """
    #     Text is saved to JSON files with 2 keys
    #         One as the extraction property as key, and as value the object identifiying the original PDF
    #         One as the "content" as key, and as value the dictionnary containing the line number for key and line as value
    #     """
    #     print('--- FINAL TEXT')
    #     print(type(self.text), self.text)
    #
    #
    #     text_dict = dict_from_text(self.text)
    #     # final_dict = dict_from_dict(self,text_dict)
    #     # json_from_dict(self,final_dict)
    #
    #
    # def save_tables(self):
    #     """
    #     Tables are saved as RDF graph
    #         Certain cells are considered as Headers (for lines or columns), sometimes cells of pivot table or agregating cells
    #         Every non header cell is identified with its value, type and closest X and Y header cell
    #     """
    #
    #     pdf_name = self.name.replace('-decrypted', '')
    #     prefix = self.directory +'/' +'extracted_files_' + pdf_name
    #     if not os.path.exists(prefix):
    #         os.makedirs(prefix)
    #     print('--- FINAL TABLES')
    #     for i in range(self.n_tables):
    #         print(getattr(self,'df_{}'.format(i)))
    #         self.tables[i].to_csv(prefix + '/' + '{}_table_{}.csv'.format(pdf_name, i), encoding='utf-8')


# %% BEGINNING OF PROGRAM

def main():
    # choose options for scrapping pdf
    parser = argparse.ArgumentParser()
    parser.add_argument('--path_pdf', type=str)
    parser.add_argument('--flavor', type=str, choices=["stream", "lattice"], default="lattice",
                        help=" 'lattice' = separation lines of cell written, 'stream' = separation lines of cell not written")
    # parser.add_argument('--type_pdf', type=str,choices=["generic","paper","cois_EFSA"],default='generic')
    args = parser.parse_args()

    # renaming document cleanly
    # new_name = args.path_pdf.replace('\\','/').replace(' ','_').replace(',','_')
    # os.rename(args.path_pdf,new_name)
    # args.path_pdf = new_name

    # execute program
    pdf = PDF(args.path_pdf, "all", args.flavor, 75, False)


if __name__ == '__main__':
    main()

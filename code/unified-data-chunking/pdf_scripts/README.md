# pdf-integration

Main file is scrapdf.py
It uses the .py files of folder scripts

Sample call: `scrapdf.py --path_pdf name_of_pdf.pdf --flavor stream` 

* 'path_pdf' is the path to the pdf file to be ingested

* 'flavor' is an option with two values: `stream` and `lattice`.  By default, the lattice value is used. If the input contains a table without visible lines (separators), use stream instead. 


The PDF will be translated (with links to original pdf) into :
* .nt files for graphs
* .json file for text

Limits:
* huge PDFs may take a very long time 
* no meaningful extraction can be obtained from image-based PDFs

These scripts are developed in pdf-integration.
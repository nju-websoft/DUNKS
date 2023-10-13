# THESE SCRIPTS ARE DEVELOPED IN PDF-INTEGRATION PROJECT
import re
import regex

from functools import reduce
from .utils import table_identifier
from .prepare_text import allowed
import rdflib
PDFTABLEXTR = rdflib.Namespace("http://tableXtr.pdf/")

#%% TAKE OFF DF FROM TEXT (tuples & string)

#%%#%% SUB FUNCTIONS

def fuzzy_extract(qs, ls, i):
    """
    matches 'qs' in 'ls' if up to i mistakes

    @var qs [string], short query
    @var ls [string], long query
    
    @returns [string], matching
    """
    qs = re.escape(qs)
    res = regex.search('('+qs+')'+'{e<'+str(i)+'}',ls)
    if res :
        return res.group()

def update_k(k,k_stop,n):
    """
    k increase by one and should go from k+1 to n then from 0 to k_stop - 1

    @var k [int], current index
    @var k_stop [int], real limit index
    @var n [int], traditional limit index
    
    @returns [int], updated k
    """
    if k_stop == 0 :
        return k + 1
    else : 
        if k == k_stop - 1 :
            return n
        elif k == n - 1 :
            return 0
        else :
            return k + 1

def update_cell_in_text(matches,match,text_element,matching,k_stop,k):
    text_element = text_element.replace(matching,'',1).rstrip().lstrip()
    match = True
    matches = matches + 1
    k_stop = k
    return(matches,match,text_element,k_stop)

def update_text_in_cell(matches,match,cell,text_element,matching,k_stop,k):
    cell = cell.replace(matching,'',1).rstrip().lstrip()
    text_element = ''
    matches = matches + 1
    return(matches,match,cell,text_element,k_stop)


#%%#%% MAIN FUNCTION

def text_without_df(text,df,k_stop,index_graph,directory_pdf,name_pdf,graph_position):
    """"
    takes off dataframe content of df (in order to delete it) cell by cell from scrapped text

    @var text [list], text scrapped from pdf
    @var df [dataframe], structured dataframe to be taken off text
    @var k_stop [int], index of previous line of which cell was taken off
    @var index_graph [int], index of table df
    @var directory_pdf [string], directory of pdf
    @var name_pdf [string], name of pdf
    @var graph_position [boolean], are the graphs' (their uri) position to be put in the text?
 
    @returns k_stop, text [int,list]
    """

    matches = 0
    index_first_cell_matching = -1

    for i in range(df.shape[0]):
        for j in range(df.shape[1]):
            cell = str(df.iloc[i,j])
            if cell == "nan" or cell == "#new_paragraph": # not to be compared cells
                continue
            else :
                match = False
                k = k_stop               
                while k < len(text) and not match:
                    if isinstance(text[k],tuple): # not to be compared lines
                        k = update_k(k,k_stop,len(text))
                    else :
                        if cell in text[k]:
                            matches,match,text[k],k_stop = update_cell_in_text(matches,match,text[k],cell,k_stop,k)
                        elif text[k] in cell and text[k]!= '':
                            matches,match,cell,text[k],k_stop = update_text_in_cell(matches,match,cell,text[k],text[k],k_stop,k)
                        elif len(cell) >= 5 and len(text[k]) >= 5 : # elements need to be long enough for comparing
                            if len(cell) <= len(text[k]):
                                fuzzymatch = fuzzy_extract(cell, text[k],2)
                                if fuzzymatch:
                                    matches,match,text[k],k_stop = update_cell_in_text(matches,match,text[k],fuzzymatch,k_stop,k)        
                            else :
                                fuzzymatch = fuzzy_extract(text[k],cell,2)
                                if fuzzymatch:
                                    matches,match,cell,text[k],k_stop = update_text_in_cell(matches,match,cell,text[k],fuzzymatch,k_stop,k)
                    if matches == 1:
                        index_first_cell_matching = k
                    k = update_k(k,k_stop,len(text))

    n1 = len(text)
    if index_first_cell_matching >= 0 and graph_position == True:
        text.insert(index_first_cell_matching,(index_graph,PDFTABLEXTR[table_identifier(directory_pdf,index_graph,name_pdf)]))
    text = [line for line in text if allowed(line)] 
    n2 = len(text)

    return max(0,n2 - (n1 - k_stop)), text

def text_without_df_full(self,graph_position):
    """"
    text_without_df for all tables

    @var self.df_i [df], table i of the graph
    @var self.n_tables [int], number of tables in the graph
    @var graph_position [boolean], are the graphs' (their uri) position to be put in the text?
    """
    k_stop = 0
    for i in range(self.n_tables): # take off content of scrapped tables
        k_stop, self.text = text_without_df(self.text,getattr(self,'df_{}'.format(i)),k_stop,i,self.directory,self.name,graph_position)


#%% TEXT IN PARAGRAPHS

def text2paragraphs(self):
    """
    turns the text into a list of paragraphs

    @var text [list], text scrapped from pdf
    """
    i_start,i_end, n = 0, 0, len(self.text)
    while i_end < n :
        if isinstance(self.text[i_end],tuple) : # uris of table left in a line alone
            if i_start != i_end : 
                self.text[i_start:i_end] = [reduce(lambda i, j: i + ' ' + j, self.text[i_start:i_end])] 
                n = n - (i_end - i_start) + 1
                i_start = i_start + 1
            i_start = i_start + 1
            i_end = i_start           
        elif self.text[i_end] == "#new_paragraph" :  # indicator of a new paragraph
            del self.text[i_end]
            if i_start != i_end : 
                self.text[i_start:i_end] = [reduce(lambda i, j: i + ' ' + j, self.text[i_start:i_end])] 
                n = n - (i_end - i_start) 
                i_start = i_start + 1
            else :
                n = n - 1
            i_end = i_start   
        else : # other lines
            i_end = i_end + 1

    
#%% BOUNDING TEXT (rdflib & string)

#%%#%% SUB FUNCTIONS

def linking_conjunctions(text):
    """"
    join lines if conjunction links them

    @var text [list], text scrapped from pdf
    
    @returns [list], cleaned text
    """
    conjunctions = ('of','for','from','and',',')
    i, n = 0, len(text)
    while i + 1 < n :
        if text[i].endswith(conjunctions):
            text[i:i+2] = [reduce(lambda i, j: i + ' ' + j, text[i:i+2])] 
            i , n = i - 1 , n - 1
        i = i + 1
    return text

def rdflib_fullstop(text,i_start,i_final,n):
    """"
    actions if rdflib with graph_position in line

    @var text [list], text scrapped from pdf
    @var i_start [int], beginning of sentence
    @var i_final [int], end of sentence
    @var n [int], number of lines 
    """
    sentence_finished = True
    if i_start != i_final:
        text[i_start:i_final] = [reduce(lambda i, j: i + ' ' + j, text[i_start:i_final])] 
        n = n - (i_final - i_start) + 1
        i_start = i_start + 1
    i_start = i_start + 1
    i_end = i_start 
    return(text,sentence_finished,i_start,i_end,n)   

def merging_fullstop(text,i_start,i_final,n):
    """"
    actions if end of sentence (.)

    @var text [list], text scrapped from pdf
    @var i_start [int], beginning of sentence
    @var i_final [int], end of sentence
    @var n [int], number of lines 
    """
    sentence_finished = True
    text[i_start:i_final] = [reduce(lambda i, j: i + ' ' + j, text[i_start:i_final])] 
    n = n - (i_final - i_start) + 1
    i_start = i_start + 1
    i_end = i_start 
    return(text,sentence_finished,i_start,i_end,n)   

def stopping_fullstop(text,i_start,i_final,n):
    """"
    actions if not a sentence (.)

    @var text [list], text scrapped from pdf
    @var i_start [int], beginning of sentence
    @var i_final [int], end of sentence
    @var n [int], number of lines 
    """
    sentence_finished = True
    if i_start != i_final - 1:
        text[i_start:i_final] = [reduce(lambda i, j: i + ' ' + j, text[i_start:i_final])] 
        n = n - (i_final - i_start) + 1
    i_start = i_start + 1
    i_end = i_start 
    return(text,sentence_finished,i_start,i_end,n)   

def adding_fullstop(text):
    """"
    joins elements of a list of strings so that the sentences (begins with capital letter, ends with point) are not split

    @var text [list], list of strings (usually sentences)
    
    @returns [list], cleaned text
    """
    i_start, i_end, n = 0, 0, len(text)
    while i_end < n :
        sentence_finished = False
        while not sentence_finished:
            if i_end < n and isinstance(text[i_end],rdflib.term.URIRef) : #rdflib item
                text,sentence_finished,i_start,i_end,n = rdflib_fullstop(text,i_start,i_end,n)
            else :   # normal event
                if i_end + 1 < n and text[i_start][0].isupper() and text[i_start][-1]!="." and text[i_end + 1][0].islower(): 
                    if text[i_end + 1][-1]==".":
                        text,sentence_finished,i_start,i_end,n = merging_fullstop(text,i_start,i_end + 2,n)
                    else : 
                        i_end=i_end+1
                else : 
                    text,sentence_finished,i_start,i_end,n = stopping_fullstop(text,i_start,i_end + 1,n)
    return text

def closing_parenthesis(text):
    """"
    join elements of a list of strings so that all the parenthesis are closed 

    @var text [list], list of strings (usually list of sentences)
    
    @returns [list], cleaned text
    """
    i_start, i_end, n = 0, 0, len(text)
    number_opening_parentesis = 0
    number_closing_parentesis = 0
    while i_end < n :
        if isinstance(text[i_end],rdflib.term.URIRef) :
            sentence_finished = True
            if i_start != i_end :
                text[i_start:i_end] = [reduce(lambda i, j: i + ' ' + j, text[i_start:i_end])] 
                n = n - (i_end - i_start) + 1
                i_start = i_start + 1
            i_start = i_start + 1
            i_end = i_start
        else :          
            number_opening_parentesis = number_opening_parentesis + text[i_start].count('(')
            number_closing_parentesis = number_closing_parentesis + text[i_start].count(')')
            sentence_finished = False
            while not sentence_finished and i_end < n : # Ajout
                if i_start != i_end :
                    number_opening_parentesis = number_opening_parentesis + text[i_end].count('(')
                    number_closing_parentesis = number_closing_parentesis + text[i_end].count(')')
                if number_opening_parentesis > number_closing_parentesis : 
                    i_end=i_end+1
                else :
                    sentence_finished = True
                    text[i_start:i_end+1] = [reduce(lambda i, j: i + ' ' + j, text[i_start:i_end+1])]
                    n = n - (i_end - i_start) 
                    i_start = i_start + 1
                    i_end = i_start
            if not sentence_finished :
                text[i_start:i_end+1] = [reduce(lambda i, j: i + ' ' + j, text[i_start:i_end+1])] 
    return text

#%%#%% MAIN FUNCTION

#%%
def sentence_bounding(text):
    """"
    joins elements of a list of strings so that the elements make sense

    @var text [list], list of strings (usually sentences)
    
    @returns [list], cleaned text
    """

    return(linking_conjunctions(adding_fullstop(closing_parenthesis(text))))


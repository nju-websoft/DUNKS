# THESE SCRIPTS ARE DEVELOPED IN PDF-INTEGRATION PROJECT
import pandas as pd
import numpy as np

from statistics import mean
from .utils import table_identifier

import rdflib
PDFTABLEXTR = rdflib.Namespace("http://tableXtr.pdf/")
import string
signs = string.punctuation.replace('.','')

#%% INTRA (NAIVE)

#%% SUB FUNCTION ########

def naive_merge_intra_columns_df(df):
    
    """
    merges columns inside df according to easy-to-implement heuristics
    
    @var df [dataframe] 

    @returns [df], cleaned df
    """

    # for 3 columns

    ## if first column only one letters strings
    k,l=df.shape
    column_mistaken = True
    if l == 3 :
        for element in df[0]:
            if not (str(element)=='nan' or len(str(element))<=2):
                column_mistaken = False
    else : 
        column_mistaken = False
    ## dropping columns and setting index
    if column_mistaken :
        df[0] = df.fillna('')[0] + df.fillna('')[1]
        del df[1]
        df.rename(columns = {2: 1}, inplace = True)
        df.replace('', np.nan,inplace= True)
    
    return df

def naive_merge_intra_lines_df(df):
    
    """
    merges columns inside df according to easy-to-implement heuristics
    
    @var df [dataframe]

    @returns [df], cleaned df
    """
    
    # for 2 columns or more

    ## if only one cell is not empty in the row (one can reduce number of columns)
    k,l=df.shape
    lines_to_be_dropped = []
    if k >= 3 and l >= 2 :  
        for i in reversed(range(1,k)):
            not_empty_cells = 0
            # number of columns required for check
            if l <= 3 :
                start = 0
            else : 
                start = 1
            # checking empty cells of columns
            for j in range(start,l):
                if not pd.isnull(df.iloc[i,j]) :
                    not_empty_cells  =  not_empty_cells + 1
            # operating merge
            if not_empty_cells  == 1 :
                lines_to_be_dropped.append(i)
                row = [np.nan if str(a)=='nan' and str(b)=='nan' else str(b) if str(a)=='nan' else str(a) if str(b)=='nan' else '{} {}'.format(str(a),str(b))                
                for (a,b) in zip(df.iloc[i-1,:],df.iloc[i,:])]
                df.iloc[i-1,:] = row
    ## dropping columns and setting index
    df.drop([df.index[i] for i in lines_to_be_dropped],inplace = True)
    df.reset_index(drop=True,inplace = True)
    
    return df

def naive_merge_intra_df(df):
    """
    merges columns and lines inside df according to easy-to-implement heuristics
    
    @var df [dataframe] 

    @returns [df], cleaned df
    """
    df = naive_merge_intra_columns_df(df)
    df = naive_merge_intra_lines_df(df)
    return df
    
#%% MAIN FUNCTION ########

def naive_merge_intra_tables(self,flavor):
    """
    merges columns and lines inside df according to easy-to-implement heuristics, for all tables
    
    @var self.df_i [df], table i of the graph 
    @var self.n_tables [int], number of tables in the graph
    @var flavor [string], type of tables in PDF : "lattice" = separation lines of cell written, "stream" = separation lines of cell not written
    """
    if flavor == 'stream':
        for j in range(self.n_tables):
            setattr(self, 'df_{}'.format(j), naive_merge_intra_df(getattr(self,'df_{}'.format(j))))


#%% INTER

#%% SUB FUNCTION ########

def comparable_cell(cell):
    """
    converts string into float if it seems to be one
    
    @var cell [obj] 
    
    @returns [obj] 
    """
    if isinstance(cell,str) :
        cell = cell.replace(',','.').translate(str.maketrans('', '', signs)).replace(' ','').replace('–','').replace('.','')
        try :
            cell=float(cell)
        except :
            pass
        print(cell,type(cell))
    return cell

def same_type(line_above,line_beneath):
    """
    compare element by element of two lists
    
    @var line_above [list] 
    @var line_beneath [list] 
    
    @returns same_type [list] 1 if elements have same type, 0 otherwise
    """
    n=len(line_above)
    same_type = [0]*n
    for i in range(n):
        cell_above = comparable_cell(line_above[i])
        cell_beneath = comparable_cell(line_beneath[i])
        if type(cell_above) == type(cell_beneath):
            same_type[i] = 1
    return same_type

def same_length(line_above,line_beneath):
    """
    compare element by element of two lists
    
    @var line_above [list] 
    @var line_beneath [list] 
    
    @returns same_length [list] ratio underneath one of length of characters if above 0.1
    """
    n=len(line_above)   
    same_length= [0]*n
    eliminated = False
    for i in range(n):
        a = len(str(line_above[i]))
        b = len(str(line_beneath[i]))
        num = min(a,b)
        den = max(a,b)
        if den>0:
            same_length[i] = num/den
        else :
            same_length[i] = 0
        if same_length[i] < 0.10 and a>0 and b>0:
            eliminated = True
    if eliminated :
        return [0]*n
    else :
        return same_length

def similarity(line_above,line_beneath):
    """   
    @var line_above [list] 
    @var line_beneath [list] 
    
    @returns [float] score of similarity out of same_length and same_type
    """
    return 0.5 * mean(same_type(line_above,line_beneath)) + 0.5 * mean(same_length(line_above,line_beneath))

def last_header(row,j) :
    """
    determines if j is the last header or not

    @var row [dataframe] row considered
    @var j [int] float name of column
    
    @returns [boolean] 
    """
    last_header = False
    try :
        if row[str(j)] and row[str(j+1)]:
            last_header = True
    except Exception:
        if row[j] and row[j+1]:
            last_header = True
    return last_header

def find_i_start(df):
    """
    determines start of datacells before YHeaderCells
    
    @var df [dataframe] 
    
    @returns [int] 
    """
    #df = df.replace(np.nan, 'Those two lines are most probably not linked' ,regex=True )
    k,l = df.shape
    i=1
    sim= 0
    while i+1 < k and sim <= 0.75 : # when similarity above a certain score those are datacells
        temp_line_above = ['' if x==np.nan else x for x in list(df.iloc[i,:])]
        temp_line_beneath = ['' if x==np.nan else x for x in list(df.iloc[i+1,:])]
        line_above = []
        line_beneath = []
        for j in range(len(temp_line_above)):
            if temp_line_above[j]!='-' and temp_line_beneath[j]!='-' :
                line_above.append(temp_line_above[j])
                line_beneath.append(temp_line_beneath[j])
        sim=similarity(line_above,line_beneath)
        print(line_above)
        print(line_beneath)
        print(sim)
        i=i+1
    if i - 1 < 1 :
        by_default = True
    else :
        by_default = False
    i_start = max(i-1,1)
    #print('THIS IS I START', i_start)
    return by_default,i_start

def find_j_start(df,i_start):
    """
    determines start of datacells before XHeaderCells
    
    @var df [dataframe] 
    @var i_start [int] start of datacells before YHeaderCells

    @returns [int] 
    """
    k,l = df.shape
    end_headers = False
    j_start = 0
    while j_start+1 < l and not end_headers :
        if not df.iloc[i_start:,j_start].isnull().values.any() : 
            # if no null values for column then end of headers (not any True = all False)
            end_headers = True
        elif not df.iloc[:i_start,j_start+1].isnull().values.all():
            # if one non null value in YHeader for next column then end of headers (not all True = any False)
            end_headers = True
        elif not df.iloc[i_start:,j_start:j_start+2].isnull().apply(lambda row: last_header(row,j_start),axis=1).isnull().values.any() :
            # if for every null cell of column j there is a non-null cell in column j+1 (not any True [here it means empty empty])
            end_headers = True
        else :
            j_start = j_start + 1
    j_start = j_start + 1
    return j_start

def datacell_start(df):
    """"
    determines start of datacells before HeaderCells
    
    @var df [dataframe] 
    
    @returns i_start, j_start [tuple] start of datacells before YHeaderCells, before XHeaderCells
    """
    k,l=df.shape
    _, i_start = find_i_start(df)
    j_start = find_j_start(df,i_start)
    return i_start, j_start  

def df_empty(self,s,i,j,tmp_n, graph_position):

    """
    updates indexes if df empty, updates graph_position
    
    @var self.df_i [df], table i of the graph
    @var self.n_tables [int], number of tables in the graph 
    @var self.text [list], text of PDF  
    @var i [int], index of first dataframe
    @var j [int], index of second dataframe 
    @var s [int], number of tables
    @var graph_position [boolean], are the graphs' (their uri) position to be put in the text?

    @returns s,i,j [int]
    """
    empty = True

    while i < tmp_n and empty :
        if getattr(self,'df_{}'.format(i)).empty :
            delattr(self,'df_{}'.format(i))
            if graph_position :
                setattr(self, 'text', delete_tuple(self.text,i))
            self.n_tables = self.n_tables - 1
            i, j = i + 1, j + 1
        else : 
            empty = False

    print("HERE IS MY DATA", self.n_tables)
    return s,i,j


def merge_ok(self,i,j,k):
    """
    checks if merging of two dataframes possible according to closeness of text (both are datacells rather than heading) 
    
    @var self.df_i [df], table i of the graph
    @var self.n_tables [int], number of tables in the graph
    @var i [int], index of first dataframe to compare
    @var j [int], index of second dataframe to compare
    @var k [int], number of lines in first dataframe

    @returns [boolean]
    """
    if k > 1 :
        tmp_df = pd.concat([getattr(self,'df_{}'.format(i)).loc[k-2:k-1,:], getattr(self,'df_{}'.format(j))], ignore_index=True) #.to_frame().T
        #print('BEG OF TMP_DF')
        #print(tmp_df)
        #print('END OF TMP_DF')
        by_default, i_start = find_i_start(tmp_df)
        if i_start == 1 and not by_default :
            return True

def tuple2string(text,directory_pdf,name_pdf,i,s):
    """
    turns tuple of (dataframe index, dataframe URI) into dataframe URI while merging tables
    
    @var text [string], text of PDF
    @var directory_pdf [string], directory of pdf
    @var name_pdf [string], name of pdf
    @var i [int], dataframe index
    @var s [int], number of tables

    @returns text [string], cleaned text
    """
    for k,element in enumerate(text):
        if isinstance(element,tuple):
            if element[0] == i :
                text[k] = PDFTABLEXTR[table_identifier(directory_pdf,s,name_pdf)]
                return text
    return text

def delete_tuple(text,j):
    """
    delete tuple of unmerged tables
    
    @var text [string], text of PDF
    @var j [int], dataframe previous index before merge

    @returns text [string], cleaned text
    """
    for k,element in enumerate(text):
        if isinstance(element,tuple):
            if element[0] == j:
                del text[k]
                return text
    return text

def actions_to_merge(self,i,j,s,graph_position):
    """
    when merging : concatenates dataframes and updates graph_position
    
    @var self.df_i [df], table i of the graph
    @var self.n_tables [int], number of tables in the graph 
    @var self.text [list], text of PDF  
    @var i [int], index of first dataframe
    @var j [int], index of second dataframe 
    @var s [int], number of tables
    @var graph_position [boolean], are the graphs' (their uri) position to be put in the text?
    """
    setattr(self,'df_{}'.format(s), pd.concat([getattr(self,'df_{}'.format(i)), getattr(self,'df_{}'.format(j))], ignore_index=True))
    if graph_position :
        setattr(self, 'text', tuple2string(self.text,self.directory,self.name,i,s))
        setattr(self, 'text', delete_tuple(self.text,j))
    delattr(self, 'df_{}'.format(j))
    self.n_tables = self.n_tables - 1

def update_s_i(self,i,j,s,graph_position):
    """
    updates index of first dataframe to compare when merge does not occur, updates graph_position
    
    @var self.df_i [df], table i of the graph
    @var self.n_tables [int], number of tables in the graph 
    @var self.text [list], text of PDF  
    @var i [int], index of first dataframe
    @var j [int], index of second dataframe 
    @var s [int], number of tables
    @var graph_position [boolean], are the graphs' (their uri) position to be put in the text?

    @returns s,i [int]
    """
    setattr(self,'df_{}'.format(s),getattr(self,'df_{}'.format(i)))
    setattr(self,'df_{}'.format(s+1),getattr(self,'df_{}'.format(j)))
    if graph_position :
        setattr(self, 'text', tuple2string(self.text,self.directory,self.name,i,s))
        setattr(self, 'text', tuple2string(self.text,self.directory,self.name,j,s+1))
    return(s+1,j)

def update_s_i_j(self,i,j,s,graph_position):
    """
    updates index of first dataframe to compare when dfj is empty, updates graph_position
    
    @var self.df_i [df], table i of the graph
    @var self.n_tables [int], number of tables in the graph 
    @var self.text [list], text of PDF  
    @var i [int], index of first dataframe
    @var j [int], index of second dataframe 
    @var s [int], number of tables
    @var graph_position [boolean], are the graphs' (their uri) position to be put in the text?

    @returns s,i,j [int]
    """
    setattr(self,'df_{}'.format(s),getattr(self,'df_{}'.format(i)))
    delattr(self,'df_{}'.format(j))
    if graph_position :
        setattr(self, 'text', tuple2string(self.text,self.directory,self.name,i,s))
        setattr(self, 'text', delete_tuple(self.text,j))
    self.n_tables = self.n_tables - 1
    return(s+1,j+1,j+2)

def tuple2URI(text): 
    """
    replaces tuple by URI of graph position
 
    @var text [list], text of PDF
    """
    match = False
    j = 0
    if text:
        while not match and j < len(text):
            if isinstance(text[j],tuple):
                match = True
                text[j] = text[j][1]
            else :
                j = j + 1

#%% MAIN FUNCTION ########

def merge_inter(self,graph_position):
    """
    try to merge tables according to closeness of text (both are datacells rather than heading) 

    @var self.df_i [df], table i of the graph
    @var self.n_tables [int], number of tables in the graph 
    @var graph_position [boolean], are the graphs' (their uri) position to be put in the text?
    """
    s, i, j = 0, 0, 1
    tmp_n = self.n_tables
    
    s,i,j = df_empty(self,s,i,j,tmp_n, graph_position)
    if i < tmp_n :
        setattr(self,'df_{}'.format(s),getattr(self,'df_{}'.format(i)))

    while j < tmp_n :
        k,l = getattr(self,'df_{}'.format(i)).shape
        if getattr(self,'df_{}'.format(j)).empty :
            s,i,j = update_s_i_j(self,i,j,s,graph_position)
            s,i,j = df_empty(self,s,i,j,tmp_n, graph_position)
            print(self.n_tables)
        elif l == getattr(self,'df_{}'.format(j)).shape[1]:
            if merge_ok(self,i,j,k):
                actions_to_merge(self,i,j,s,graph_position)
            else :
               s,i = update_s_i(self,i,j,s,graph_position)
        else :
            s,i = update_s_i(self,i,j,s,graph_position)
        j = j + 1

    if graph_position :
        tuple2URI(self.text)

    for i in range(self.n_tables,tmp_n):
        try : 
            delattr(self,'df_{}'.format(i))
        except :
            pass
#%% INTRA

#%%#### SUBFUNCTIONS

def merge_intra_df(df,i_start, j_start):
    """
    merges headers if they do not seem to aggregate
    
    @var df [dataframe] 
    @var i_start [int] start of datacells before YHeaderCells
    @var j_start [int] start of datacells before XHeaderCells

    @returns i_start updated accordingly
    """
    k,l=df.shape
    lines_to_be_dropped = []
    if i_start > 0 : 
        for i in reversed(range(1,i_start)):
            successive_headers = False
            for j in range(j_start,l-1):
                if not pd.isnull(df.iloc[i-1,j]) and not pd.isnull(df.iloc[i-1,j+1]):
                    successive_headers = True
            if successive_headers :
                lines_to_be_dropped.append(i)
                row = [np.nan if str(a)=='nan' and str(b)=='nan' else str(b) if str(a)=='nan' else str(a) if str(b)=='nan' else '{} {}'.format(str(a),str(b))                
                for (a,b) in zip(df.iloc[i-1,:],df.iloc[i,:])]
                df.iloc[i-1,:] = row
    df.drop([df.index[i] for i in lines_to_be_dropped],inplace = True)
    df.reset_index(drop=True,inplace = True)
    i_start = i_start - len(lines_to_be_dropped)
    return i_start

#%% MAIN FUNCTION ########

def merge_intra(self,flavor):
    """
    merge_intra_df for all tables 

    @var self.df_i [df], table i of the graph
    @var self.n_tables [int], number of tables in the graph 
    @var flavor [string], type of tables in PDF : "lattice" = separation lines of cell written, "stream" = separation lines of cell not written
    @var graph_position [boolean], are the graphs' (their uri) position to be put in the text?
    """
    for i in range(self.n_tables):
        
        # dataframe chosen
        df = getattr(self,'df_{}'.format(i))

        # distinguishing header cells from data cells
        i_start, j_start = datacell_start(df)
        print(i_start, j_start)
        if flavor == 'stream':
            i_start = merge_intra_df(df,i_start,j_start)

        setattr(self, 'df_{}'.format(i),df) 
        setattr(self, 'i{}_start'.format(i),i_start) 
        setattr(self, 'j{}_start'.format(i),j_start)


        

     


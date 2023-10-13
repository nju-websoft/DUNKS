# THESE SCRIPTS ARE DEVELOPED IN PDF-INTEGRATION PROJECT
import numpy as np

#%% CLEAN TABLES

#%% SUB FUNCTIONS ########

def clean_line_break_df(row):
    """"
    takes off '\n' python line breaks of dataframes

    @var row [pandas.Series], row of dataframe
    
    @returns row [pandas.Series], cleaned row of dataframe
    """
    if isinstance(row, str):
        return row.replace('\n',' ').rstrip().lstrip()
    else : # for instance graph position
        return row

def select_accurate_tables(self, threshold):
    """"
    eliminates tables that are not accurate enough

    @var self.df_i [df], table i of the graph
    @var self.n_tables [int], number of tables in the graph
    @var threshold [int], from 0 to 100 miminum of accuracy of tables to be scrapped
    """
    j = 0
    for i in range(self.n_tables):
        if abs(self.tables[i].parsing_report['accuracy']) >= threshold : 
            setattr(self, 'df_{}'.format(j), self.tables[i].df.replace(r'^\s*$', np.nan, regex=True))
            j = j + 1
    for i in range(j,self.n_tables):
        try : 
            delattr(self,'df_{}'.format(i))
        except :
            pass
    self.n_tables = j

def clean_tables(self):
    """"
    cleans tables

    @var self.df_i [df], table i of the graph
    """
    for j in range(self.n_tables):
        setattr(self, 'df_{}'.format(j), getattr(self,'df_{}'.format(j)).applymap(clean_line_break_df)) # take off line breaks '\n' in cells
        getattr(self,'df_{}'.format(j)).dropna(how='all',axis=0,inplace=True) # drop empty lines
        getattr(self,'df_{}'.format(j)).dropna(how='all',axis=1,inplace=True) # drop empty columns
        getattr(self,'df_{}'.format(j)).reset_index(drop=True,inplace = True) # adjust indexes of lines
        getattr(self,'df_{}'.format(j)).columns = list(range(getattr(self,'df_{}'.format(j)).shape[1])) # adjust indexes of columns

#%% MAIN FUNCTION ########

def prepare_tables(self, threshold):
    """"
    eliminates tables that are not accurate enough and clean the rest

    @var self.df_i [df], table i of the graph
    @var self.n_tables [int], number of tables in the graph
    @var threshold [int], from 0 to 100 miminum of accuracy of tables to be scrapped
    """
    select_accurate_tables(self, threshold)
    clean_tables(self)
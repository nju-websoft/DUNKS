# THESE SCRIPTS ARE DEVELOPED IN PDF-INTEGRATION PROJECT

import re

#%% CLEAN TEXT

#%% SUB FUNCTIONS ########

def is_empty_lines(line):
    """"
    determines which lines are empty

    @var line [string], string studied
    
    @returns [boolean], True if line is not empty
    """
    if re.match('(.)+',line) :
        return True
    else :
        return False
    
def is_spaces_lines(line):
    """"
    determines which lines are blank spaces

    @var line [string], string studied
    
    @returns [boolean], True if line is not blank spaces
    """
    
    if re.match('^( )+',line):
        if re.match('^( )+[^ ]+',line):
            return True
        else :
            return False
    else : 
        return True
    
def allowed(line):
    """"
    determines which lines are empty or full of blank spaces

    @var line [string], string studied
    
    @returns [boolean], True if line is nor empty nor only blank spaces
    """
    if isinstance(line,str):
        return is_spaces_lines(line) and is_empty_lines(line)
    else :
        return True


#%% MAIN FUNCTION ########

def prepare_text(self):
    """"
    turns string text into list
    removes empty lines and empty spaces
    adds an identifier #new_paragraph to keep structure of text

    @var self.text [string], text of PDF
    """
    if self.text :
        self.text = re.sub('((\n)( )*){2,}','\n #new_paragraph', self.text) # identify paragraphs (two line breaks or more)
        self.text = self.text.split('\n') # line per line
        i = 0
        n = len(self.text)
        while i < n :
            if '#new_paragraph' in self.text[i]:
                self.text[i] = self.text[i].replace('#new_paragraph','')
                self.text.insert(i,'#new_paragraph') # specify paragraphs (two line breaks or more)
                n = n + 1
                i = i + 1
            i = i + 1
        self.text = [line for line in self.text if allowed(line)] # deleting lines with blank or empty spaces
        self.text = [re.sub('( )+',' ',word).rstrip().lstrip() for word in self.text] # deleting long white spaces in lines


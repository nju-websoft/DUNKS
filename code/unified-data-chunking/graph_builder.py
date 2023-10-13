import json
import os
import shutil
import signal
import traceback
import zlib
import magic
from concurrent import futures
import re
import string
import contractions

import pandas
import xmltodict
from bs4 import BeautifulSoup
from docx import Document
from pdf_scripts.scrapdf import PDF
from rdflib import QB, Graph
from rdflib.plugins.shared.jsonld import util
import sys, getopt
import fcntl

project_root = '.'

tmpfile_store_path = f"{project_root}/.hidden/tmp_files"
file_store_path = None
output_path = None
verbose = False

term_id = 0
seg_id = 0

dataset_id = 0
dataset_cnt_path = f"{project_root}/.hidden/dataset_cnt.txt"
assert os.path.isfile(dataset_cnt_path)
with open(dataset_cnt_path, 'r') as f:
    dataset_id = int(f.read())


edge_dict, entity_dict, literal_dict, count_dict = {}, {}, {}, {}
term_list, triple_list = [], []
seg_list = []
ignored_dataset_list = []
max_filesize = 1024 * 1024 * 1024
format_dict = json.load(open(f"{project_root}/resource/mimetype_mapping.json", encoding='utf-8'))
magic_tool = magic.Magic(mime=True)


def init_dataset_dict(argv):
    global output_path
    dataset_dict = {}
    try:
        opts, args = getopt.getopt(argv, "hi:p:o:v", ["help", "input_file=", "input_path=", "output_path=", "verbose"]) # h: help, i: input, o: output
    except getopt.GetoptError:
        print('usage: graph_builder.py [-i|-p] <input_file|input_path> -o <output_path>')
        sys.exit(2)

    for opt, arg in opts:
        if opt == "-h":
            print('usage: graph_builder.py [-i|-p] <input_file|input_path> -o <output_path>')
            sys.exit()
        elif opt in ("-i", "--input_file"):
            dataset_dict = init_datafile(arg)
        elif opt in ("-p", "--input_path"):
            dataset_dict = init_collection(arg)
        elif opt in ("-o", "--output_path"):
            output_path = arg
            if not os.path.exists(output_path):
                print(f"output path {output_path} does not exist, created it.")
                os.makedirs(output_path)
        elif opt in ("-v", "--verbose"):
            global verbose
            verbose = True
    return dataset_dict

def format_detect(filename):
    file_type = magic_tool.from_file(filename)
    if file_type in format_dict:
        file_type = format_dict[file_type]
    else:
        file_type = "Unknown"
    return file_type

def init_datafile(filename):
    global dataset_id
    assert os.path.isfile(filename), f"{filename} is not a file"
    file_type = format_detect(filename)
    dataset_id += 1
    dataset_dict = {dataset_id :{'data':[{'data_format': file_type,'data_filename': filename}]}}
    return dataset_dict

def init_collection(filepath):
    global dataset_id
    assert os.path.isdir(filepath), f"{filepath} is not a directory"
    dataset_dict = {}
    dataset_dir = []
    for filename in os.listdir(filepath):
        if os.path.isdir(os.path.join(filepath, filename)):
            dataset_dir.append(os.path.join(filepath, filename))
    
    for dataset in dataset_dir:
        dataset_id += 1
        dataset_dict[dataset_id] = {'data': []}
        for filename in os.listdir(dataset):
            if os.path.isfile(os.path.join(dataset, filename)):
                file_type = format_detect(os.path.join(dataset, filename))
                dataset_dict[dataset_id]['data'].append({'data_format': file_type,'data_filename': os.path.join(dataset, filename)})

    return dataset_dict

def add_seg(text):
    global seg_list, seg_id, dataset_id
    seg_id += 1
    seg_list.append([dataset_id, seg_id, text.replace("\t", " ")])

def add_term(text, kind):
    global dataset_id, term_id
    global term_list, edge_dict, entity_dict, literal_dict
    if kind == 0:
        if text == "":
            term_id += 1
            node_id = term_id
            entity_dict[("", term_id)] = term_id
            term_list.append([dataset_id, term_id, "", 0])
        else:
            if text not in entity_dict:
                term_id += 1
                entity_dict[text] = term_id
                term_list.append([dataset_id, term_id, text, 0])
            node_id = entity_dict[text]
    elif kind == 1:
        if text not in literal_dict:
            term_id += 1
            node_id = term_id
            literal_dict[text] = term_id
            term_list.append([dataset_id, term_id, text, 1])
        node_id = literal_dict[text]
    else:
        if text not in edge_dict:
            term_id += 1
            edge_dict[text] = term_id
            term_list.append([dataset_id, term_id, text, 2])
        node_id = edge_dict[text]
    return node_id


def add_triple(sub, pre, obj):
    global dataset_id
    global triple_list,  count_dict
    triple_list.append([dataset_id, sub, pre, obj])
    for i in [sub, pre, obj]:
        if i not in count_dict:
            count_dict[i] = 0
        count_dict[i] += 1


def convert_df(df):
    if df.shape[0] == 1 or df.shape[1] == 1:
        return
    global term_id, edge_dict, entity_dict
    flag = True
    headers = df.columns
    for h in headers:
        if not pandas.isna(h):
            add_term(str(h), 2)

    for index, row in df.iterrows():
        if not flag:
            row_id = add_term("", 0)
        else:
            if pandas.isna(row[headers[0]]):
                continue
            text = str(row[headers[0]])
            row_id = add_term(text, 0)
        for key in headers:
            if (flag and key == headers[0]) or pandas.isna(key) or pandas.isna(row[key]):
                continue
            value = str(row[key])
            key = str(key)
            if value != "":
                if value in entity_dict:
                    obj_id = add_term(value, 0)
                else:
                    obj_id = add_term(value, 1)
                add_triple(row_id, edge_dict[key], obj_id)


def convert_csv(filename):
    try:
        df = pandas.read_csv(filename, low_memory=False)
    except pandas.errors.EmptyDataError:
        return
    convert_df(df)


def convert_xls(filename):
    df = pandas.read_excel(filename, sheet_name=None)
    for sheet_name in df.keys():
        sheet_df = df[sheet_name]
        convert_df(sheet_df)


def convert_rdf(filename):
    global term_id
    g = Graph()
    g.parse(filename)
    for s, p, o in g:

        s_label = util.split_iri(s)[1]
        p_label = util.split_iri(p)[1]
        o_label = util.split_iri(o)[1]

        # print(s_label, p_label, o)
        sub_id = add_term(s_label, 0)
        pre_id = add_term(p_label, 2)
        if o_label is None:
            o_label = str(o)
            obj_id = add_term(o_label, 1)
        else:
            obj_id = add_term(o_label, 0)

        add_triple(sub_id, pre_id, obj_id)


def dict_generator(indict, pre_node_id=None, pre_edge_id=None):
    global term_id
    node_id = None
    if indict is None:
        return

    elif isinstance(indict, dict):
        if len(indict) != 0:
            node_id = add_term("", 0)
            for key, value in indict.items():
                edge_id = add_term(key, 2)
                dict_generator(value, node_id, edge_id)
        else:
            return

    elif isinstance(indict, list) or isinstance(indict, tuple):
        if len(indict) != 0:
            node_id = add_term("", 0)
            for value in indict:
                key = ""
                edge_id = add_term(key, 2)
                if isinstance(value, list) or isinstance(value, tuple) or isinstance(value, dict):
                    str_node = json.dumps(value)
                    dict_generator(str_node, node_id, edge_id)
                elif isinstance(value, str):
                    len_str = len(value.split(" "))
                    for i in range(len_str, 0, 500):
                        segment_str = " ".join(value.split(" ")[i:i + 500])
                        dict_generator(segment_str, node_id, edge_id)
        else:
            return

    elif isinstance(indict, str):
        if indict != "":
            node_id = add_term(indict, 1)

    if pre_node_id is not None and node_id is not None:
        add_triple(pre_node_id, pre_edge_id, node_id)


def convert_json(filename):
    with open(filename, encoding="utf-8") as jsonfile:
        row_data = json.load(jsonfile)
        dict_generator(row_data)


def convert_xml(filename):
    with open(filename, encoding="utf-8") as xmlfile:
        # convert to json first
        row_data = xmltodict.parse(xmlfile.read())
        dict_data = json.loads(json.dumps(row_data))
        dict_generator(dict_data)

def remove_emoji(text):
    emoji_pattern = re.compile("["
                           u"U0001F600-U0001F64F"  # emoticons
                           u"U0001F300-U0001F5FF"  # symbols & pictographs
                           u"U0001F680-U0001F6FF"  # transport & map symbols
                           u"U0001F1E0-U0001F1FF"  # flags (iOS)
                           u"U00002702-U000027B0"
                           u"U000024C2-U0001F251"
                           "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', text)

def clean_text(text):
    text = text.lower()
    text = text.translate(str.maketrans(string.punctuation, ' ' *len(string.punctuation)))
    term_list = []
    for term in text.split():
        if len(term) < 40:
            term_list.append(term)
    text = " ".join(term_list)
    text = remove_emoji(text)
    text = contractions.fix(text)
    return text


def convert_txt(filename):
    with open(filename, encoding="utf-8") as txtfile:
        file_str = txtfile.read()
        file_str = clean_text(file_str)
        file_str_list = file_str.split(" ")
        for i in range(0, len(file_str_list), 500):
            add_seg(" ".join(file_str_list[i:i + 500]))


def convert_html(filename):
    soup = BeautifulSoup(open(filename, encoding='utf-8'), features="lxml")
    content = soup.get_text()
    tmp_filename = tmpfile_store_path + os.path.split(filename)[1].replace('.html', '.txt')
    with open(tmp_filename, 'w+', encoding='utf-8') as txtfile:
        txtfile.write(content)
    convert_txt(tmp_filename)
    os.remove(tmp_filename)


def convert_docx(filename):
    document = Document(filename)
    content = ''
    for p in document.paragraphs:
        content = f'{content}{p.text}/n'
    tmp_filename = tmpfile_store_path + os.path.split(filename)[1].replace('.docx', '.txt')
    with open(tmp_filename, 'w+', encoding='utf-8') as txtfile:
        txtfile.write(content)
    convert_txt(tmp_filename)
    os.remove(tmp_filename)


def convert_doc(filename):
    os.system(f"libreoffice --headless --convert-to docx {filename} --outdir {tmpfile_store_path}")
    convert_docx(filename)
    os.remove(filename)


def convert_pdf(filename):
    pdf = PDF(filename, "all", "lattice", 75, False)
    if pdf.text is not None:
        content = " \n".join(pdf.text)
    else:
        content = ""
    tmp_filename = tmpfile_store_path + os.path.split(filename)[1].replace('.pdf', '.txt')
    with open(tmp_filename, 'w+', encoding='utf-8') as txtfile:
        txtfile.write(content)
    convert_txt(tmp_filename)
    os.remove(tmp_filename)
    try:
        os.remove(f"{tmpfile_store_path}{os.path.splitext(filename)[0]}-decrypted.pdf")
    except:
        pass


def convert_gzip(filename):
    new_filename = filename.replace("application.x-gzip", "gz").replace("octet-stream", "gz")
    os.rename(filename, new_filename)
    unziped_filename = new_filename.replace(".gz", "")
    os.system("gunzip " + new_filename)
    detect_format = magic.from_file(unziped_filename, mime=True)
    if detect_format not in format_dict:
        return
    detect_format = format_dict[detect_format]
    if detect_format == 'csv':
        convert_csv(unziped_filename)
    elif detect_format == 'rdf':
        convert_rdf(unziped_filename)
    elif detect_format == 'pdf':
        convert_pdf(unziped_filename)
    elif detect_format == 'json':
        convert_json(unziped_filename)
    elif detect_format == 'xml':
        convert_xml(unziped_filename)
    elif detect_format == 'txt':
        convert_txt(unziped_filename)
    elif detect_format == 'docx':
        convert_docx(unziped_filename)
    elif detect_format == 'doc':
        convert_doc(unziped_filename)
    elif detect_format == 'html':
        convert_html(unziped_filename)
    elif detect_format in ['xls', 'xlsx']:
        convert_xls(unziped_filename)
    os.remove(unziped_filename)


def decompress_file(infile, dst):
    infile = open(infile, 'rb')
    dst = open(dst, 'wb')
    decompressed = zlib.decompressobj()
    data = infile.read()
    dst.write(decompressed.decompress(data))
    dst.write(decompressed.flush())
    infile.close()
    dst.close()


'''
return 0->successful     1->unhandled     2->error while converting
'''
def convert_file(filename, format_str=''):
    global dataset_id, verbose
    out_file = tmpfile_store_path + filename
    try:
        if format_str == 'csv':
            convert_csv(out_file)
        elif format_str == 'rdf':
            convert_rdf(out_file)
        elif format_str == 'pdf':
            convert_pdf(out_file)
        elif format_str == 'json':
            convert_json(out_file)
        elif format_str == 'xml':
            convert_xml(out_file)
        elif format_str == 'txt':
            convert_txt(out_file)
        elif format_str == 'docx':
            convert_docx(out_file)
        elif format_str == 'doc':
            convert_doc(out_file)
        elif format_str == 'html':
            convert_html(out_file)
        elif format_str in ['xls', 'xlsx']:
            convert_xls(out_file)
        elif format_str == 'gzip':
            convert_gzip(out_file)
        else:
            return 1
    except Exception as e:
        traceback.print_exc()
        return 2
    if verbose:
        print(f"Complete {filename}")
    return 0


def handler(signum, frame):
    raise Exception("task timeout.")

def store_file(filename, data_list:list):
    with open(os.path.join(output_path, filename), 'a+', encoding='utf-8') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        for data in data_list:
            f.write('\t'.join([str(item) for item in data]) + '\n')


def task(file_list, ds_id):
    global term_id, seg_id
    global entity_dict, edge_dict, count_dict, literal_dict
    global term_list, triple_list
    global ignored_dataset_list
    global seg_list
    global dataset_id
    term_id = 0
    seg_id = 0
    edge_dict = {}
    entity_dict = {}
    count_dict = {}
    literal_dict = {}
    term_list = []
    triple_list = []
    seg_list = []

    dataset_id = ds_id
    file_cnt = len(file_list)
    unhandled_cnt = 0
    done_cnt = 0
    sum_filesize = 0
    oversize = False

    for file in file_list:
        filename = file['data_filename']
        in_file = filename
        out_file = tmpfile_store_path + os.path.split(filename)[1]
        shutil.copy(in_file, out_file)
        sum_filesize += os.path.getsize(out_file)
        if sum_filesize >= max_filesize:
            oversize = True
            break

    try:
        signal.signal(signal.SIGALRM, handler=handler)
        signal.alarm(3600)
        for file in file_list:
            filename = file['data_filename']
            format_str = file['data_format']

            if not oversize:
                success = convert_file(os.path.split(filename)[1], format_str)
                if success == 0:
                    done_cnt += 1
                elif success == 1:
                    unhandled_cnt += 1
                else:
                    pass
                if len(triple_list) >= 10000000:
                    oversize = True
            else:
                break
    except Exception as e:
        return dataset_id, file_cnt, 0, file_cnt
    finally:
        for file in file_list:
            try:
                filename = file['data_filename']
                os.remove(tmpfile_store_path + os.path.split(filename)[1])
            except:
                pass
        signal.alarm(0)

    if oversize:
        ignored_dataset_list.append(dataset_id)
        return dataset_id, file_cnt, 0, file_cnt

    try:
        store_file('term.tsv', term_list)
        store_file('triple.tsv', triple_list)
        store_file('text.tsv', seg_list)
        print(f"Complete dataset_id: {dataset_id}")
        return dataset_id, file_cnt, done_cnt, unhandled_cnt
    except Exception as e:
        traceback.print_exc()
        return dataset_id, file_cnt, 0, file_cnt


def main(args):
    dataset_dict = init_dataset_dict(args)

    dataset_id_list = list(dataset_dict.keys())
    with futures.ProcessPoolExecutor() as pool:
        work_dict = {pool.submit(task, dataset_dict[i]['data'], i): i for i in dataset_id_list}
        for future in futures.as_completed(work_dict):
            try:
                ds_id, file_cnt, done_cnt, undo_cnt = future.result()
            except:
                traceback.print_exc()
                continue
    
    with open(f"{project_root}/.hidden/dataset_cnt.txt", 'w') as f:
        f.write(str(dataset_id))


if __name__ == '__main__':
    import sys, getopt
    main(sys.argv[1:])

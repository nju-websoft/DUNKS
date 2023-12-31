import os
import copy
import fcntl
import signal
import traceback
from concurrent import futures

import pandas as pd

term_list, triple_list = [], []
verbose = False
chunk_num, chunk_size = 1, 20
entity_list, property_list = [], []
edp_count_dict, property_count_dict = {}, {}
entity_edp, entity_property, entity_triple = {}, {}, {}
property_value_count_dict = {}
dataset_id = -1


def init_input_path(path):
    assert os.path.isdir(path), f"{path} is not a directory"
    # |--input_path
    #     |--term.csv
    #     |--triple.csv
    dataset_dict = {}
    for filename in os.listdir(path):
        if os.path.isfile(os.path.join(path, filename)):
            name = filename.split('.')[0]
            dataset_dict[name] = os.path.join(path, filename)
    assert 'term' in dataset_dict and 'triple' in dataset_dict, \
        f"please provide term.tsv and triple.tsv generated by graph_builder.py"
    return dataset_dict


def read_input_file(name):
    df = pd.read_csv(name, sep='\t', header=None)
    return [tuple(row) for row in df.values]


def print_usage():
    print('usage: python summary_generator.py -i <input_path> -o <output_path> [-n <chunk_num>] [-k <chunk_size>]')


def check_output_path(output_path):
    if not os.path.exists(output_path):
        print(f"output path {output_path} does not exist, created it.")
        os.makedirs(output_path)


def opt_handle(argv):
    input_dict = {}
    output_path = ''
    try:
        opts, args = getopt.getopt(argv[1:], "hvi:o:n:k:",
                                   ["help", "verbose", "input_path=", "output_path=", "chunk_num=", "chunk_size="])
    except getopt.GetoptError:
        print_usage()
        sys.exit(2)

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print_usage()
            sys.exit(0)
        elif opt in ("-i", "--input_path"):
            input_dict = init_input_path(arg)
        elif opt in ("-o", "--output_path"):
            output_path = arg
            check_output_path(output_path)
        elif opt in ("-v", "--verbose"):
            global verbose
            verbose = True
        elif opt in ("-n", "--chunk_num"):
            global chunk_num
            chunk_num = int(arg)
            assert chunk_num > 0, "chunk num should be positive"
        elif opt in ("-k", "--chunk_size"):
            global chunk_size
            chunk_size = int(arg)
            assert chunk_size > 0, "chunk size should be positive"

    return input_dict, output_path


def edp_analyse():
    global entity_list
    global property_list
    global property_count_dict
    global edp_count_dict
    global entity_edp
    global entity_property
    global entity_triple
    global property_value_count_dict
    entity_list = [term[0] for term in term_list if term[2] == 0]
    property_list = [term[0] for term in term_list if term[2] == 2]
    property_count_dict = {prop: 0 for prop in property_list}
    property_value_count_dict = {prop: {} for prop in property_list}
    # {entity_id: [fp, bp]}
    entity_property = {entity: [set(), set()] for entity in entity_list}
    # {entity_id: edp_id}
    entity_edp = {entity: -1 for entity in entity_list}
    # {entity_id: set(triples)}
    entity_triple = {entity: {} for entity in entity_list}
    edp_count_dict = {}
    for sub, pre, obj in triple_list:
        property_count_dict[pre] += 1
        if sub in entity_property:
            entity_property[sub][1].add(pre)  # bp
        if obj in entity_property:
            entity_property[obj][0].add(pre)  # fp
        if obj not in property_value_count_dict[pre]:
            property_value_count_dict[pre][obj] = 0
        property_value_count_dict[pre][obj] += 1
        if sub not in property_value_count_dict[pre]:
            property_value_count_dict[pre][sub] = 0
        property_value_count_dict[pre][sub] += 1
        if sub in entity_triple:
            if pre not in entity_triple[sub]:
                entity_triple[sub][pre] = []
            entity_triple[sub][pre].append((sub, pre, obj))
        if obj in entity_triple:
            if pre not in entity_triple[obj]:
                entity_triple[obj][pre] = []
            entity_triple[obj][pre].append((sub, pre, obj))

    edp_id = 0
    # {edp: edp_id}
    edp_dict = {}
    for entity_id, edp in entity_property.items():
        if len(edp[0]) == 0 and len(edp[1]) == 0:
            continue
        edp_tuple = (tuple(edp[0]), tuple(edp[1]))
        if edp_tuple not in edp_dict:
            edp_id += 1
            edp_dict[edp_tuple] = edp_id
        entity_edp[entity_id] = edp_dict[edp_tuple]
        if edp_dict[edp_tuple] not in edp_count_dict:
            edp_count_dict[edp_dict[edp_tuple]] = 0
        edp_count_dict[edp_dict[edp_tuple]] += 1


def construct_universe():
    global edp_count_dict
    global property_count_dict
    edp_set = {edp_id for edp_id in edp_count_dict}
    property_set = {property_id for property_id in property_count_dict}

    return {'edp': edp_set,
            'property': property_set,
            }


def construct_candidate_units():
    global entity_list
    global entity_edp
    global entity_property
    return {entity: {
        'edp': {entity_edp[entity]},
        'property': entity_property[entity][0].union(entity_property[entity][1])
    } for entity in entity_list}


def calculate_weight(universe):
    global edp_count_dict
    global property_count_dict
    edp_weight_dict = {edp_id: 0 for edp_id in universe['edp']}
    property_weight_dict = {property_id: 0 for property_id in universe['property']}
    # edp_weight
    edp_total = 0
    for edp_id, count in edp_count_dict.items():
        edp_total += count
    for edp_id, count in edp_count_dict.items():
        edp_weight_dict[edp_id] = count / edp_total
    # property_weight
    property_total = 0
    for property_id, count in property_count_dict.items():
        property_total += count
    for property_id, count in property_count_dict.items():
        property_weight_dict[property_id] = count / property_total

    return {
        'edp': edp_weight_dict,
        'property': property_weight_dict,
    }


def chunk_selection(universe, candidate_units, weight):
    selected_num = -1
    selected_entity_list = []

    def universe_uncovered(u):
        return len(u['property']) > 0 \
               or len(u['edp']) > 0

    while len(selected_entity_list) < chunk_num:
        if selected_num >= len(selected_entity_list):
            # 上一轮覆盖没有选择任何的实体（candidate units的数量为0)
            break
        selected_num = len(selected_entity_list)
        universe_cop = copy.deepcopy(universe)
        while universe_uncovered(universe_cop) and len(candidate_units) > 0:
            selected_unit = None
            selected_entity = None
            max_score = 0
            for entity_id, unit in candidate_units.items():
                score = 0
                for new_covered_edp in universe_cop['edp'].intersection(unit['edp']):
                    score += weight['edp'][new_covered_edp]
                for new_covered_property in universe_cop['property'].intersection(unit['property']):
                    score += weight['property'][new_covered_property]
                if score > max_score:
                    selected_unit = unit
                    selected_entity = entity_id
                    max_score = score
            if max_score == 0:
                break
            selected_entity_list.append(selected_entity)
            universe_cop['edp'].difference_update(selected_unit['edp'])
            universe_cop['property'].difference_update(selected_unit['property'])
            del candidate_units[selected_entity]
            if len(selected_entity_list) >= chunk_num:
                break
    return selected_entity_list


def triple_selection_for_entity(entity_id, weight):
    global entity_triple
    selected_triple = []
    selected_num = -1

    sorted_triple_ids = sorted(entity_triple[entity_id].keys(), key=lambda x: weight['property'][x],
                               reverse=True)
    while len(selected_triple) < chunk_size:
        if selected_num >= len(selected_triple):
            break
        selected_num = len(selected_triple)
        for pre in sorted_triple_ids:
            triples = entity_triple[entity_id][pre]
            if len(triples) == 0:
                continue
            max_score = -1
            max_triple = None
            for triple in triples:
                sub = triple[0]
                obj = triple[2]
                triple_score = 0
                if sub == entity_id:
                    triple_score = property_value_count_dict[pre][obj]
                elif obj == entity_id:
                    triple_score = property_value_count_dict[pre][sub]
                if triple_score > max_score:
                    max_score = triple_score
                    max_triple = triple
            selected_triple.append(max_triple)
            entity_triple[entity_id][pre].remove(max_triple)
            if len(selected_triple) >= chunk_size:
                return selected_triple
    return selected_triple


def triple_selection(selected_entity_list, weight):
    global dataset_id
    chunk_list = []
    chunk_id = 0
    for entity_id in selected_entity_list:
        selected_triple = triple_selection_for_entity(entity_id, weight)
        chunk_id += 1
        for sub, pre, obj in selected_triple:
            chunk_list.append((dataset_id, chunk_id, sub, pre, obj))
    return chunk_list


def chunk_summarization():
    global verbose
    global dataset_id
    # first construct the universe and candidate_units
    universe = construct_universe()
    candidate_units = construct_candidate_units()
    # calculate the weight of each element
    weight = calculate_weight(universe)
    # greedy chooses a set that contains the maximum weight of uncovered elements.
    if verbose:
        print(f"Starting chunk selection for dataset {dataset_id}")
    # first stage: entity-level greedy coverage
    selected_entity_list = chunk_selection(universe, candidate_units, weight)
    if verbose:
        print(f"Starting triple selection for dataset {dataset_id}")
    # second stage: triple-level greedy coverage
    chunk_list = triple_selection(selected_entity_list, weight)

    if verbose:
        print(f"Completed summary generation for dataset {dataset_id}")
    return chunk_list


def data_preprocess(input_dict):
    global triple_list
    global term_list
    global dataset_id
    triple_list = [(s, p, o) for did, s, p, o in read_input_file(input_dict['triple']) if did == dataset_id]
    term_list = [(term_id, label, kind) for did, term_id, label, kind in read_input_file(input_dict['term']) if
                 did == dataset_id]
    if verbose:
        print(f"Get term and triple information for dataset {dataset_id}.")
    edp_analyse()
    if verbose:
        print(f"Complete edp analysis for dataset {dataset_id}.")


def handler(signum, frame):
    raise Exception("Task timeout.")


def store_file(filename, output_path, data_list: list):
    with open(os.path.join(output_path, filename), 'a+', encoding='utf-8') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        for data in data_list:
            f.write('\t'.join([str(item) for item in data]) + '\n')
    return 1


def get_datasets(input_dict):
    return list(set([t[0] for t in read_input_file(input_dict['triple'])]))


def task(input_dict, output_path, did):
    global dataset_id
    dataset_id = did
    try:
        signal.signal(signal.SIGALRM, handler=handler)
        signal.alarm(3600)
        data_preprocess(input_dict)
        summary = chunk_summarization()
    except Exception as e:
        traceback.print_exc()
        sys.exit(2)

    try:
        success = store_file(f"summay.tsv", output_path, summary)
    except Exception as e:
        success = 0
        traceback.print_exc()

    return success


def main(argv):
    input_dict, output_path = opt_handle(argv)
    dataset_id_list = get_datasets(input_dict)
    with futures.ProcessPoolExecutor() as pool:
        work_dict = {pool.submit(task, input_dict, output_path, i) for i in dataset_id_list}
        for future in futures.as_completed(work_dict):
            try:
                success = future.result()
            except Exception as e:
                traceback.print_exc()
                continue


if __name__ == '__main__':
    import getopt
    import sys

    main(sys.argv)

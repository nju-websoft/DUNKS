from FlagEmbedding import FlagModel
import os
import json
import csv
from tqdm import tqdm

os.environ["CUDA_VISIBLE_DEVICES"] = "4"

data_path = "/path_to_data"
model_path = '/path_to_checkpoint'
rerank_path = '/path_to_baseline'

def cal_score(model, query, passages):
    res = []
    q_embeddings = model.encode_queries([query["question"]], batch_size=512)
    p_embeddings = model.encode([p["text"] for p in passages], batch_size=512)
    scores = q_embeddings @ p_embeddings.T
    # print(scores)
    for i in range(len(scores[0])):
        res.append((query['q_id'], passages[i], scores[0][i]))
    res.sort(key=lambda x:x[2], reverse=True)
    return res

with open(f'{model_path}/ntcir/BM25_metadata_top10_reranking.tsv', 'w+') as fout:
    print(f'ntcir metadata')
    with open(f'{rerank_path}/ntcir/metadata/BM25_top10_metadata_split_test.json', 'r') as fin:
        test_json = json.load(fin)
    model = FlagModel(f'{model_path}/ntcir/metadata', query_instruction_for_retrieval="Represent this sentence for searching relevant passages: ") 
    for qp in tqdm(test_json):
        for res in cal_score(model, {"q_id": qp["q_id"], "question": qp["question"]}, qp["ctxs"]):
            fout.write(f'{res[0]}\t{int(res[1]["c_id"])}\t{res[2]}\n')

chunk_num = 100
chunk_size = 10
mapping_path = f'{data_path}/ntcir_chunk_{chunk_num}_{chunk_size}/ntcir_chunk_{chunk_num}_{chunk_size}_mapping.txt'
id2dataset = {}
last_id = 0
with open(mapping_path, 'r+', encoding='utf-8') as fp:
    for row in csv.reader(fp, delimiter='\t'):
        dataset_id = int(row[0])
        start_id = int(row[1])
        end_id = int(row[2])
        last_id = max(last_id, end_id)
        for i in range(start_id, end_id):
            id2dataset[i] = dataset_id
mapping_path = f'{data_path}/ntcir_text_{chunk_num}/ntcir_text_{chunk_num}_mapping.txt'
with open(mapping_path, 'r+', encoding='utf-8') as fp:
    for row in csv.reader(fp, delimiter='\t'):
        dataset_id = int(row[0])
        start_id = int(row[1])
        end_id = int(row[2])
        for i in range(last_id + start_id - 1, last_id + end_id - 1):
            id2dataset[i] = dataset_id
with open(f'{model_path}/ntcir/BM25_data_chunk_{chunk_num}_{chunk_size}_top10_reranking.tsv', 'w') as fout:
    print(f'ntcir data_chunk_{chunk_num}_{chunk_size}')
    with open(f'{rerank_path}/ntcir/data/BM25_top10_data_chunk_{chunk_num}_{chunk_size}_split_test.json', 'r') as fin:
        test_json = json.load(fin)
    model = FlagModel(f'{model_path}/ntcir/data_chunk_{chunk_num}_{chunk_size}', query_instruction_for_retrieval="Represent this sentence for searching relevant passages: ")    
    for qp in tqdm(test_json):
        dataset_id_set = set()
        for res in cal_score(model, {"q_id": qp["q_id"], "question": qp["question"]}, qp["ctxs"]):
            dataset_id = id2dataset[int(res[1]["c_id"])]
            if dataset_id in dataset_id_set:
                continue
            dataset_id_set.add(dataset_id)
            fout.write(f'{res[0]}\t{dataset_id}\t{res[2]}\n')
                

        

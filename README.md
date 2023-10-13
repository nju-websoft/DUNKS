# DUNKS

This is the source code and data with the paper "DUNKS: Chunking and Summarizing Large and Heterogeneous Web Data for Dataset Search".

---

## Requirements

This code is based on Python 3.9+, and the partial list of the required packages is as follow.

- beautifulsoup4
- camelot_py
- contractions
- pikepdf
- python_docx
- python_magic
- rdflib
- tika
- xmltodict
- flag-embedding
- torch
- transformers
- ranx

```
pip install -r requirements.txt
```

---

## Unified Data Chunking

```
python ./code/unified-data-chunking/graph_builder.py [-i|-p] <input_file|input_path> -o <output_path>
```

- [-i|--input_file]: path to a single file

- [-p|--input_path]: path to the input folder

- [-o|--output_path]: path to the output folder

Notice: only one of -i and -p can be used

The structure of the input folder:

```
    ./input_folder
    |--dataset1
        |--file1.json
        |--file2.csv
    |--dataset2
        |--file1.json
        |--file2.csv
```

The input dataset can contain multiple heterogeneous data files. Currently supported data formats include:
- `.txt`, `.pdf`, `.html`, `.doc`, `.docx`
- `.csv`, `.xls`, `.xlsx` 
- `.json`, `.xml`
- `.rdf`, `.nt`, `.owl`

The generated files in the output folder:
```
    ./output_folder
    |--term.tsv
    |--text.tsv
    |--triple.tsv
```

The structrue of the output file is as follows:
- `term.tsv`: dataset_id`\t`term_id`\t`term_text
- `text.tsv`: dataset_id`\t`passage_id`\t`passage_text
- `triple.tsv`: dataset_id`\t`subject_id`\t`predicate_id`\t`object_id


---

## Multi-Chunk Summarization

```
python ./code/multi-chunk-summarization/summary_generator.py -i <input_path> -o <output_path> -n <chunk_num> -k <chunk_size>
```
- [-p|--input_path]: path to the input folder, usually it is the output folder of the previous step

- [-o|--output_path]: path to the output folder

- [-n|--chunk_num]: the maximum number of chunks retained in the summary

- [-k|--chunk_size]: the maximum number of triples in a summarized chunk

The structure of the input folder:

```
    ./input_folder
    |--term.tsv
    |--triple.tsv
```

The generated files in the output folder:

```
    ./output_folder
    |--summary.tsv
```

The structrue of the output file is as follows:
- `summary.tsv`: dataset_id`\t`chunk_id`\t`subject_id`\t`predicate_id`\t`object_id

---

## Chunk-based Dataset Reranking

We implement monoBERT, BGE, and BGE-reranker as dense reranking models, see code in `./code/chunk-based-dataset-reranking/` for details. We use [ranx](https://github.com/AmenRa/ranx) for normalizing and fusing metadata-based and data-based relevance scores.

---

## Evaluation

All the results for reranking experiments on test collection [NTCIR-E](https://ntcir.datasearch.jp/data_search_1/) and [ACORDAR](https://github.com/nju-websoft/ACORDAR) are at `./data/results` in TREC format as follows.

```
1 Q0 32907 1 1.3371933160530833 mixed
1 Q0 31665 2 1.2344413177975981 mixed
1 Q0 1670 3 0.816091260131519 mixed
```

---

## Citation
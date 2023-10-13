#! /bin/bash

export  CUDA_VISIBLE_DEVICES=0

test_ntcir_metadata() {
    python run_monobert_nticr_e.py \
        --seed 42 --epoch_num 5 \
        --model_name /path_to_model \
        --test_path ./data/ntcir15/metadata/BM25_top10_metadata_split_test.json \
        --dev_path ./data/ntcir15/metadata/BM25_top10_metadata_split_dev.json \
        --init_checkpoint True \
        --init_checkpoint_path ./outputs/ntcir15/monoBERT_metadata_monobert/pytorch_model.bin \
        --results_save_path ./results/ntcir15/ \
        --only_eval True \
        --task metadata \
        --topk 10
}

test_ntcir_data() {
    python run_monobert_nticr_e.py \
        --seed 42 --epoch_num 5 \
        --model_name /path_to_model \
        --test_path ./data/ntcir15/data/BM25_top10_data_chunk_$1_$2_split_test.json \
        --dev_path ./data/ntcir15/metadata/BM25_top10_metadata_split_dev.json \
        --init_checkpoint True \
        --init_checkpoint_path ./outputs/ntcir15/monoBERT_data_chunk_$1_$2_monobert/pytorch_model.bin \
        --results_save_path ./results/ntcir15/ \
        --only_eval True \
        --task data_chunk_$1_$2 \
        --topk 10
}

test_ntcir_metadata

test_ntcir_data 100 20
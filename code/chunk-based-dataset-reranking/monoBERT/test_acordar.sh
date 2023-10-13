#! /bin/bash

export  CUDA_VISIBLE_DEVICES=0

test_acordar_metadata() {
    python run_monobert_acordar.py \
        --seed 42 --epoch_num 5 \
        --model_name /path_to_model \
        --test_dir_path ./data/acordar1/metadata/ \
        --init_checkpoint True \
        --checkpoint_dir ./outputs/acordar/monoBERT_metadata_monobert/fold_$1 \
        --only_eval True \
        --task metadata \
        --fold $1 \
        --topk 10
}

test_acordar_data() {
    python run_monobert_acordar.py \
        --seed 42 --epoch_num 5 \
        --model_name /path_to_model \
        --train_dir_path ./data/acordar1/data/ \
        --test_dir_path ./data/acordar1/data/ \
        --init_checkpoint True \
        --checkpoint_dir ./outputs/acordar/monoBERT_data_chunk_$2_$3_monobert/fold_$1 \
        --only_eval True \
        --task data_chunk_$2_$3 \
        --fold $1 \
        --topk 10
}

for fold in {0..4}
do
    test_acordar_metadata $fold
done


for fold in {0..4}
do
    test_acordar_data $fold 100 20
done
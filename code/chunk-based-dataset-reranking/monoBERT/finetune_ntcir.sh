#! /bin/bash

export  CUDA_VISIBLE_DEVICES=0,1,2,3

train_ntcir_data() {
    python run_monobert_nticr_e.py \
        --seed 42 --epoch_num 5 \
        --model_name /path_to_model \
        --train_path ./data/ntcir/data/data_chunk_$1_$2_split_train.json \
        --dev_path ./data/ntcir/data/data_chunk_$1_$2_split_dev.json \
        --output_dir ./outputs/ntcir/ \
        --results_save_path ./results/ntcir$5/ \
        --lr 1e-5 \
        --train_batch_size 16 \
        --gradient_accumulation_steps 16 \
        --task data_chunk_$1_$2
}

train_ntcir_data 100 20 16 1e-5
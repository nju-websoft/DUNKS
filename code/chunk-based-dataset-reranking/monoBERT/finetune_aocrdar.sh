#! /bin/bash

export  CUDA_VISIBLE_DEVICES=0,1,2,3

train_acordar1() {
    python run_monobert_acordar.py \
        --seed 42 --epoch_num 5 \
        --model_name /path_to_model \
        --train_dir_path ./data/acordar1/data/ \
        --test_dir_path ./data/acordar1/data/ \
        --lr 1e-5 \
        --train_batch_size 16 \
        --gradient_accumulation_steps 16 \
        --task data_chunk_$2_$3 \
        --fold $1
}

for fold in {0..4}
do
    train_acordar1 $fold 100 20 
done
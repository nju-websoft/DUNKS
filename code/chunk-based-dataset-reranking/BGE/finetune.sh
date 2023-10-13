
export CUDA_VISIBLE_DEVICES=0,1,2,3

train_ntcir_data() {
    torchrun --nproc_per_node 4 \
    -m FlagEmbedding.baai_general_embedding.finetune.run \
    --output_dir "./outputs/ntcir/data_chunk_$2_$3" \
    --model_name_or_path "/path_to_model" \
    --train_data "./data/ntcir/data/data_chunk_$2_$3_split_train_minedHN.jsonl" \
    --learning_rate 1e-5 \
    --fp16 \
    --num_train_epochs 5 \
    --per_device_train_batch_size 2 \
    --dataloader_drop_last True \
    --normlized True \
    --temperature 0.02 \
    --query_max_len 16 \
    --passage_max_len 512 \
    --train_group_size 10 \
    --negatives_cross_device \
    --query_instruction_for_retrieval "Represent this sentence for searching relevant passages: "
}

train_ntcir_data 100 20
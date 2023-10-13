export  CUDA_VISIBLE_DEVICES=0,1,2,3

minehn_ntcir_data() {
python -m FlagEmbedding.baai_general_embedding.finetune.hn_mine \
    --model_name_or_path "/path_to_model" \
    --input_file "./data/ntcir/data/data_chunk_$1_$2_split_train.jsonl" \
    --output_file "./data/ntcir/data/data_chunk_$1_$2_split_train_reranker_minedHN.jsonl" \
    --range_for_sampling "2-200" 
}

minehn_ntcir_data 100 10
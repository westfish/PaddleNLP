python -m paddle.distributed.launch --gpus 4,5,6,7 finetune.py \
    --model_name_or_path=t5-base \
    --dataset_name=squad \
    --output_dir=output \
    --max_source_length=1024 \
    --max_target_length=142 \
    --learning_rate=1e-4 \
    --num_train_epochs=6 \
    --logging_steps=100 \
    --save_steps=1000 \
    --seed=42 \
    --train_batch_size=8 \
    --eval_batch_size=64 \
    --warmup_proportion=0.1 \
    --device=gpu
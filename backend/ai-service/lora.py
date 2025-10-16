from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments, DataCollatorForLanguageModeling
from peft import LoraConfig, get_peft_model, TaskType
import torch
import math

# --- Модель и токенизатор ---
model = AutoModelForCausalLM.from_pretrained("./quantized_model")
tokenizer = AutoTokenizer.from_pretrained("./quantized_model")

# Убедитесь, что у токенизатора есть pad_token
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

# --- LoRA ---
lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=64,  # Увеличенный ранг
    lora_alpha=128,  # Увеличьте пропорционально
    lora_dropout=0.1  # Уменьшите dropout для большей стабильности
)
model = get_peft_model(model, lora_config)

# --- Загрузка и разделение текста на абзацы ---
with open("knowledge_base.txt", "r", encoding="utf-8") as f:
    text = f.read()

# Разделяем текст на абзацы (предполагаем, что абзацы разделены двойным переносом строки)
paragraphs = text.split("\n")  # Или "\n", если абзацы разделены одиночным переносом

# Удаляем пустые абзацы и убираем лишние пробелы
paragraphs = [p.strip() for p in paragraphs if p.strip()]

# --- Токенизация абзацев ---
max_length = 1024  # Максимальная длина токенизированного абзаца
all_examples = []
all_attention_masks = []

for paragraph in paragraphs:
    # Токенизируем абзац
    tokens = tokenizer(
        paragraph,
        max_length=max_length,
        truncation=True,
        padding=False,  # Padding будет добавлен в DataCollator
        return_tensors="pt",
        add_special_tokens=True
    )
    input_ids = tokens["input_ids"].squeeze().tolist()
    attention_mask = tokens["attention_mask"].squeeze().tolist()
    
    # Добавляем только непустые последовательности
    if len(input_ids) > 1:  # Исключаем слишком короткие абзацы (например, 1 токен)
        all_examples.append(input_ids)
        all_attention_masks.append(attention_mask)

# --- Разделение на тренировочные и валидационные данные ---
train_size = int(0.8 * len(all_examples))
train_examples = all_examples[:train_size]
eval_examples = all_examples[train_size:]
train_attention_masks = all_attention_masks[:train_size]
eval_attention_masks = all_attention_masks[train_size:]

# Создаем датасеты
train_dataset = Dataset.from_dict({"input_ids": train_examples, "attention_mask": train_attention_masks})
eval_dataset = Dataset.from_dict({"input_ids": eval_examples, "attention_mask": eval_attention_masks})

# Проверяем размер датасетов
print(f"Размер тренировочной выборки: {len(train_dataset)} примеров")
print(f"Размер валидационной выборки: {len(eval_dataset)} примеров")

# --- Рассчитываем eval_steps для 10 валидаций ---
per_device_train_batch_size = 2
num_train_epochs = 10
total_training_steps = math.ceil(len(train_dataset) / per_device_train_batch_size) * num_train_epochs
eval_steps = total_training_steps // 10

# --- Data collator ---
data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer,
    mlm=False,
    pad_to_multiple_of=8  # Оптимизация для GPU
)

# --- Настройка Trainer ---
training_args = TrainingArguments(
    output_dir="./lora_finetuned",
    per_device_train_batch_size=per_device_train_batch_size,
    per_device_eval_batch_size=2,
    num_train_epochs=num_train_epochs,
    logging_steps=eval_steps,
    save_steps=eval_steps,
    save_total_limit=1,
    eval_strategy="steps",
    eval_steps=eval_steps,
    save_strategy="steps",
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    weight_decay=0.01,
    fp16=True,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    data_collator=data_collator,
)

# --- Обучение модели ---
trainer.train()

# --- Сохранение модели ---
trainer.save_model("./lora_finetuned/best_model")
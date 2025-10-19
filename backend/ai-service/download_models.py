#!/usr/bin/env python3
"""
Скрипт для загрузки моделей с HuggingFace Hub
Запускается автоматически при старте контейнера, если модели не найдены локально
"""

import os
import logging
from huggingface_hub import snapshot_download
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация моделей на HuggingFace
MODELS_CONFIG = {
    "quantized_model": {
        "repo_id": os.getenv("BASE_MODEL_REPO", "LeoCristt/hackathon-base-model"),
        "local_path": "quantized_model",
    },
    "frida_embedding_model": {
        "repo_id": os.getenv("EMBEDDING_MODEL_REPO", "LeoCristt/hackathon-embedding-model"),
        "local_path": "frida_embedding_model",
    },
}

def model_exists(local_path):
    """Проверяет наличие модели локально"""
    path = Path(local_path)
    if not path.exists():
        return False

    # Проверяем наличие ключевых файлов
    required_files = ["config.json"]
    for file in required_files:
        if not (path / file).exists():
            return False

    return True

def download_model(repo_id, local_path, model_type="model"):
    """Загружает модель с HuggingFace Hub"""
    try:
        logger.info(f"Загрузка {model_type} из {repo_id} в {local_path}...")

        snapshot_download(
            repo_id=repo_id,
            local_dir=local_path,
            local_dir_use_symlinks=False,
            resume_download=True,
        )

        logger.info(f"✓ {model_type} успешно загружена в {local_path}")
        return True

    except Exception as e:
        logger.error(f"Ошибка загрузки {model_type} из {repo_id}: {e}")
        return False

def main():
    """Основная функция для загрузки моделей"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

    logger.info("Проверка и загрузка моделей...")

    # Загружаем базовую модель
    if not model_exists(MODELS_CONFIG["quantized_model"]["local_path"]):
        download_model(
            MODELS_CONFIG["quantized_model"]["repo_id"],
            MODELS_CONFIG["quantized_model"]["local_path"],
            "Базовая модель"
        )
    else:
        logger.info("Базовая модель уже загружена")

    # Загружаем embedding модель
    if not model_exists(MODELS_CONFIG["frida_embedding_model"]["local_path"]):
        download_model(
            MODELS_CONFIG["frida_embedding_model"]["repo_id"],
            MODELS_CONFIG["frida_embedding_model"]["local_path"],
            "Embedding модель"
        )
    else:
        logger.info("Embedding модель уже загружена")

    logger.info("Все модели готовы к использованию!")

if __name__ == "__main__":
    main()

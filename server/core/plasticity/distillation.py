import importlib.util
import json
import logging
from pathlib import Path
from typing import Any

from server.core.core_platform.errors import CortexFailure, fail
from server.core.core_platform.result import Ok, Result
from server.core.plasticity.ledger import PlasticityLedger

logger = logging.getLogger("nuxiva.plasticity.distillation")

MIN_EXAMPLES = 50
REQUIRED_MODULES = ("torch", "transformers", "peft", "bitsandbytes", "datasets", "trl")
PROMPT = "Utterance: {utterance}\nNeuron: {neuron}"


def missing_dependencies() -> list[str]:
    return [name for name in REQUIRED_MODULES if importlib.util.find_spec(name) is None]


def gpu_available() -> bool:
    if importlib.util.find_spec("torch") is None:
        return False
    import torch
    return bool(torch.cuda.is_available())


def build_dataset(ledger: PlasticityLedger, target: Path, minimum: int = MIN_EXAMPLES) -> Result[int, CortexFailure]:
    rows = ledger.examples()
    if not rows.is_ok:
        return rows
    if len(rows.value) < minimum:
        return fail("hippocampus.distillation.no_data", available=len(rows.value), needed=minimum)
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with target.open("w", encoding="utf-8") as stream:
        for neuron_id, utterance in rows.value:
            stream.write(json.dumps({"text": PROMPT.format(utterance=utterance, neuron=neuron_id)}, ensure_ascii=False) + "\n")
    target.chmod(0o600)
    return Ok(len(rows.value))


def train(dataset: Path, base_model: str, output: Path, epochs: int = 2) -> Result[dict[str, Any], CortexFailure]:
    missing = missing_dependencies()
    if missing or not gpu_available():
        return fail("hippocampus.distillation.unavailable", missing=missing, gpu=gpu_available() if not missing else False)
    import torch
    from datasets import load_dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import SFTConfig, SFTTrainer

    quantization = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True,
                                      bnb_4bit_compute_dtype=torch.bfloat16)
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    model = AutoModelForCausalLM.from_pretrained(base_model, quantization_config=quantization, device_map="auto")
    trainer = SFTTrainer(
        model=model, processing_class=tokenizer,
        train_dataset=load_dataset("json", data_files=str(dataset), split="train"),
        peft_config=LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, task_type="CAUSAL_LM"),
        args=SFTConfig(output_dir=str(output), num_train_epochs=epochs, per_device_train_batch_size=4,
                       gradient_accumulation_steps=4, learning_rate=2e-4, logging_steps=10, save_strategy="no",
                       dataset_text_field="text"),
    )
    trainer.train()
    trainer.model.save_pretrained(str(output))
    return Ok({"adapter": str(output), "base_model": base_model, "epochs": epochs})

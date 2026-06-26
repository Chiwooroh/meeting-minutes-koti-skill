#!/usr/bin/env python
"""Transcribe audio locally with Transformers Whisper and imageio-ffmpeg."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import requests
import torch
from huggingface_hub import configure_http_backend
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Transcribe audio locally with Whisper.")
    parser.add_argument("audio", nargs="+", help="Audio file paths to transcribe in order.")
    parser.add_argument("--out", required=True, help="Output Markdown transcript path.")
    parser.add_argument("--model", default="openai/whisper-small", help="Hugging Face Whisper model.")
    parser.add_argument("--language", default="korean", help="Whisper language hint.")
    return parser.parse_args()


def decode_audio(path: Path) -> np.ndarray:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        ffmpeg,
        "-nostdin",
        "-i",
        str(path),
        "-f",
        "s16le",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-",
    ]
    proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    audio = np.frombuffer(proc.stdout, np.int16).astype(np.float32) / 32768.0
    return audio


def build_pipeline(model_name: str):
    def backend_factory() -> requests.Session:
        session = requests.Session()
        session.verify = False
        return session

    configure_http_backend(backend_factory=backend_factory)
    use_cuda = torch.cuda.is_available()
    torch_dtype = torch.float16 if use_cuda else torch.float32
    print(f"Loading Whisper model from local cache or Hugging Face Hub: {model_name}")
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_name,
        torch_dtype=torch_dtype,
        low_cpu_mem_usage=True,
        use_safetensors=True,
    )
    processor = AutoProcessor.from_pretrained(model_name)
    return pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        torch_dtype=torch_dtype,
        device=0 if use_cuda else -1,
        chunk_length_s=30,
        stride_length_s=5,
    )


def main() -> None:
    args = parse_args()
    transcriber = build_pipeline(args.model)
    chunks = ["# 회의 녹취 전사", ""]
    for index, item in enumerate(args.audio, start=1):
        path = Path(item).expanduser().resolve()
        if not path.exists():
            raise SystemExit(f"Audio file not found: {path}")
        audio = decode_audio(path)
        result = transcriber(
            {"array": audio, "sampling_rate": 16000},
            generate_kwargs={"language": args.language, "task": "transcribe"},
        )
        chunks.extend([f"## 녹음 {index}: {path.name}", "", result["text"].strip(), ""])
    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(chunks).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote transcript: {out_path}")


if __name__ == "__main__":
    main()

import os
from typing import Optional, List, Dict

from dotenv import find_dotenv
from pydantic import computed_field
from pydantic_settings import BaseSettings
import torch


class Settings(BaseSettings):
    # General
    TORCH_DEVICE: Optional[str] = None

    @computed_field
    @property
    def TORCH_DEVICE_MODEL(self) -> str:
        if self.TORCH_DEVICE is not None:
            return self.TORCH_DEVICE

        if torch.cuda.is_available():
            return "cuda"

        if torch.backends.mps.is_available():
            return "mps"

        return "cpu"

    INFERENCE_RAM: int = 40 # How much VRAM each GPU has (in GB).
    VRAM_PER_TASK: float = 2.5 # How much VRAM to allocate per task (in GB).  Peak marker VRAM usage is around 3GB, but avg across workers is lower.
    DEFAULT_LANG: str = "English" # Default language we assume files to be in, should be one of the keys in TESSERACT_LANGUAGES

    SUPPORTED_FILETYPES: Dict = {
        "application/pdf": "pdf",
        #"application/epub+zip": "epub",
        #"application/x-mobipocket-ebook": "mobi",
        #"application/vnd.ms-xpsdocument": "xps",
        #"application/x-fictionbook+xml": "fb2"
    }

    # Text line Detection
    DETECTOR_BATCH_SIZE: Optional[int] = None # Defaults to 2 for CPU, 32 otherwise
    SURYA_DETECTOR_DPI: int = 96
    DETECTOR_POSTPROCESSING_CPU_WORKERS: int = 4

    # OCR
    INVALID_CHARS: List[str] = [chr(0xfffd), "�"]
    OCR_ENGINE: Optional[str] = None # Which OCR engine to use, either "surya" or "ocrmypdf".  Defaults to "ocrmypdf" on CPU, "surya" on GPU.
    OCR_ALL_PAGES: bool = False # Run OCR on every page even if text can be extracted

    ## Surya
    SURYA_OCR_DPI: int = 96
    RECOGNITION_BATCH_SIZE: Optional[int] = None # Batch size for surya OCR defaults to 8 for CPU/MPS, 256 otherwise

    ## Tesseract
    OCR_PARALLEL_WORKERS: int = 2 # How many CPU workers to use for OCR
    TESSERACT_TIMEOUT: int = 20 # When to give up on OCR
    TESSDATA_PREFIX: str = ""

    @computed_field
    def OCR_ENGINE_INTERNAL(self) -> str:
        if self.OCR_ENGINE is not None:
            return self.OCR_ENGINE

        # Does not work with mps
        if torch.cuda.is_available():
            return "surya"

        return "ocrmypdf"

    # Texify model
    TEXIFY_MODEL_MAX: int = 384 # Max inference length for texify
    TEXIFY_TOKEN_BUFFER: int = 256 # Number of tokens to buffer above max for texify
    TEXIFY_DPI: int = 96 # DPI to render images at
    TEXIFY_BATCH_SIZE: int = 2 if TORCH_DEVICE_MODEL == "cpu" else 6 # Batch size for texify, lower on cpu due to float32
    TEXIFY_MODEL_NAME: str = "vikp/texify"

    # Layout model
    SURYA_LAYOUT_DPI: int = 96
    BAD_SPAN_TYPES: List[str] = ["Caption", "Footnote", "Page-footer", "Page-header", "Picture"]
    LAYOUT_MODEL_CHECKPOINT: str = "vikp/surya_layout2"

    # Ordering model
    ORDER_BATCH_SIZE: Optional[int] = None  # Defaults to 4 for CPU/MPS, 32 otherwise

    # Final editing model
    EDITOR_BATCH_SIZE: int = 4
    EDITOR_MAX_LENGTH: int = 1024
    EDITOR_MODEL_NAME: str = "vikp/pdf_postprocessor_t5"
    ENABLE_EDITOR_MODEL: bool = False # The editor model can create false positives
    EDITOR_CUTOFF_THRESH: float = 0.9 # Ignore predictions below this probability

    # Ray
    RAY_CACHE_PATH: Optional[str] = None # Where to save ray cache
    RAY_CORES_PER_WORKER: int = 1 # How many cpu cores to allocate per worker

    # Debug
    DEBUG: bool = False # Enable debug logging
    DEBUG_DATA_FOLDER: Optional[str] = None
    DEBUG_LEVEL: int = 0 # 0 to 2, 2 means log everything

    @computed_field
    @property
    def CUDA(self) -> bool:
        return "cuda" in self.TORCH_DEVICE

    @computed_field
    @property
    def MODEL_DTYPE(self) -> torch.dtype:
        if self.TORCH_DEVICE_MODEL == "cuda":
            return torch.bfloat16
        else:
            return torch.float32

    @computed_field
    @property
    def TEXIFY_DTYPE(self) -> torch.dtype:
        return torch.float32 if self.TORCH_DEVICE_MODEL == "cpu" else torch.float16

    class Config:
        env_file = find_dotenv("local.env")
        extra = "ignore"


settings = Settings()
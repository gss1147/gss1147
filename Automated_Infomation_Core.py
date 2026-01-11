"""
GODs Strongest Soldier AI Chatbot - Information Core
Multi-format file support with optional real-time fine-tuning.

Design goals
- Broad multi-format ingestion (best-effort, dependency-aware).
- Deterministic, safe feature extraction.
- Optional online fine-tuning (Torch if available; numpy fallback otherwise).

Important
- Many formats require optional third-party libraries. If a dependency is missing,
  the reader returns a structured "requires" response rather than crashing.
"""
from __future__ import annotations

import os
import json
import pickle
import sqlite3
import threading
import time
import random
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from collections import defaultdict

# Optional scientific stack
try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None  # type: ignore

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None  # type: ignore

# Optional ML stack
try:
    import torch
except Exception:  # pragma: no cover
    torch = None  # type: ignore

# Optional parsers/media
try:
    import PyPDF2
except Exception:  # pragma: no cover
    PyPDF2 = None  # type: ignore

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None  # type: ignore

try:
    import toml
except Exception:  # pragma: no cover
    toml = None  # type: ignore

try:
    import xmltodict
except Exception:  # pragma: no cover
    xmltodict = None  # type: ignore

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore

try:
    import soundfile as sf
except Exception:  # pragma: no cover
    sf = None  # type: ignore


def _requires(name: str) -> Dict[str, Any]:
    return {"status": "requires_dependency", "dependency": name}


class MultiFormatReader:
    """Universal reader for supported formats (best-effort)."""
    def __init__(self):
        self.supported_formats = {
            # Text/data
            ".txt": self.read_text,
            ".log": self.read_text,
            ".md": self.read_text,
            ".markdown": self.read_text,
            ".csv": self.read_csv,
            ".tsv": self.read_tsv,
            ".tab": self.read_tsv,
            ".xlsx": self.read_excel,
            ".xls": self.read_excel,
            ".json": self.read_json,
            ".jsonl": self.read_jsonl,
            ".xml": self.read_xml,
            ".yaml": self.read_yaml,
            ".yml": self.read_yaml,

            # Source code / configs (treated as text)
            ".py": self.read_text,
            ".pyw": self.read_text,
            ".ipynb": self.read_text,
            ".js": self.read_text,
            ".jsx": self.read_text,
            ".ts": self.read_text,
            ".tsx": self.read_text,
            ".java": self.read_text,
            ".c": self.read_text,
            ".cpp": self.read_text,
            ".h": self.read_text,
            ".hpp": self.read_text,
            ".cs": self.read_text,
            ".go": self.read_text,
            ".rs": self.read_text,
            ".php": self.read_text,
            ".rb": self.read_text,
            ".sh": self.read_text,
            ".ps1": self.read_text,
            ".bat": self.read_text,
            ".ini": self.read_text,
            ".cfg": self.read_text,
            ".toml": self.read_toml,
            ".html": self.read_html,
            ".pdf": self.read_pdf,
            ".doc": self.read_doc,
            ".docx": self.read_docx,
            ".rtf": self.read_text,

            # Databases
            ".db": self.read_sqlite,
            ".sqlite": self.read_sqlite,
            ".sqlite3": self.read_sqlite,
            ".sql": self.read_sql_dump,

            # Binary/tabular
            ".pkl": self.read_pickle,
            ".pickle": self.read_pickle,
            ".parquet": self.read_parquet,
            ".pqt": self.read_parquet,
            ".h5": self.read_hdf5,
            ".hdf5": self.read_hdf5,
            ".feather": self.read_feather,
            ".arrow": self.read_arrow,

            # Images
            ".jpg": self.read_image,
            ".jpeg": self.read_image,
            ".png": self.read_image,
            ".gif": self.read_image,
            ".bmp": self.read_image,
            ".tiff": self.read_tiff,
            ".tif": self.read_tiff,
            ".webp": self.read_image,

            # Audio/Video (metadata + limited payload)
            ".wav": self.read_audio,
            ".flac": self.read_audio,
            ".mp3": self.read_audio,
            ".mp4": self.read_video,
            ".avi": self.read_video,
            ".mov": self.read_video,
            ".mkv": self.read_video,
        }

    def read_file(self, file_path: str) -> Dict[str, Any]:
        try:
            ext = Path(file_path).suffix.lower()
            if ext not in self.supported_formats:
                return {"status": "unsupported", "message": f"Format {ext} not supported", "file_path": file_path}

            reader = self.supported_formats[ext]
            content = reader(file_path)
            return {
                "status": "success",
                "content": content,
                "format": ext,
                "file_path": file_path,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {"status": "error", "message": str(e), "file_path": file_path}

    # ---- Text/data readers ----
    def read_text(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    def read_csv(self, file_path: str):
        if pd is None:
            return _requires("pandas")
        return pd.read_csv(file_path)

    def read_tsv(self, file_path: str):
        if pd is None:
            return _requires("pandas")
        return pd.read_csv(file_path, sep="\t")

    def read_excel(self, file_path: str):
        if pd is None:
            return _requires("pandas")
        return pd.read_excel(file_path)

    def read_json(self, file_path: str) -> Any:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def read_jsonl(self, file_path: str) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out

    def read_xml(self, file_path: str) -> Any:
        if xmltodict is None:
            return _requires("xmltodict")
        with open(file_path, "r", encoding="utf-8") as f:
            return xmltodict.parse(f.read())

    def read_yaml(self, file_path: str) -> Any:
        if yaml is None:
            return _requires("pyyaml")
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def read_toml(self, file_path: str) -> Any:
        if toml is None:
            return _requires("toml")
        with open(file_path, "r", encoding="utf-8") as f:
            return toml.load(f)

    def read_html(self, file_path: str) -> Any:
        try:
            from bs4 import BeautifulSoup  # type: ignore
        except Exception:
            return _requires("beautifulsoup4")
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
            return soup.get_text()

    def read_pdf(self, file_path: str) -> Any:
        if PyPDF2 is None:
            return _requires("PyPDF2")
        text = ""
        with open(file_path, "rb") as f:
            pdf_reader = PyPDF2.PdfReader(f)
            for page in getattr(pdf_reader, "pages", []):
                extracted = page.extract_text() or ""
                text += extracted + "\n"
        return text.strip()

    def read_doc(self, file_path: str) -> Any:
        try:
            import textract  # type: ignore
        except Exception:
            return _requires("textract")
        try:
            return textract.process(file_path).decode("utf-8", errors="ignore")
        except Exception as e:
            return {"status": "error", "message": f"textract failed: {e}"}

    def read_docx(self, file_path: str) -> Any:
        try:
            from docx import Document  # type: ignore
        except Exception:
            return _requires("python-docx")
        doc = Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs])

    # ---- Database / binary ----
    def read_sqlite(self, file_path: str) -> Any:
        if pd is None:
            return _requires("pandas")
        conn = sqlite3.connect(file_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            table_names = [row[0] for row in cursor.fetchall()]
            tables = {name: pd.read_sql_query(f"SELECT * FROM {name}", conn) for name in table_names}
            return tables
        finally:
            conn.close()

    def read_sql_dump(self, file_path: str) -> str:
        return self.read_text(file_path)

    def read_pickle(self, file_path: str) -> Any:
        with open(file_path, "rb") as f:
            return pickle.load(f)

    def read_parquet(self, file_path: str) -> Any:
        if pd is None:
            return _requires("pandas")
        try:
            return pd.read_parquet(file_path)
        except Exception:
            return _requires("pyarrow or fastparquet")

    def read_hdf5(self, file_path: str) -> Any:
        if pd is None or np is None:
            return _requires("pandas + numpy")
        try:
            import h5py  # type: ignore
        except Exception:
            return _requires("h5py")
        out: Dict[str, Any] = {}
        with h5py.File(file_path, "r") as f:
            def _visit(name, obj):
                if hasattr(obj, "shape"):
                    try:
                        out[name] = pd.DataFrame(obj[()])
                    except Exception:
                        out[name] = {"shape": getattr(obj, "shape", None)}
                else:
                    out[name] = list(getattr(obj, "keys", lambda: [])())
            f.visititems(_visit)
        return out

    def read_feather(self, file_path: str) -> Any:
        if pd is None:
            return _requires("pandas")
        try:
            return pd.read_feather(file_path)
        except Exception:
            return _requires("pyarrow")

    def read_arrow(self, file_path: str) -> Any:
        if pd is None:
            return _requires("pandas")
        try:
            import pyarrow.parquet as pq  # type: ignore
        except Exception:
            return _requires("pyarrow")
        table = pq.read_table(file_path)
        return table.to_pandas()

    # ---- Media ----
    def read_image(self, file_path: str) -> Any:
        if cv2 is None:
            return _requires("opencv-python")
        img = cv2.imread(file_path)
        if img is None:
            return {"status": "error", "message": "cv2.imread failed"}
        return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    def read_tiff(self, file_path: str) -> Any:
        try:
            from PIL import Image, ImageSequence  # type: ignore
        except Exception:
            return _requires("Pillow")
        img = Image.open(file_path)
        frames = [frame.copy() for frame in ImageSequence.Iterator(img)]
        return [self._pil_to_array(f) for f in frames]

    def _pil_to_array(self, img):  # type: ignore
        if np is None:
            return {"status": "requires_dependency", "dependency": "numpy"}
        return np.array(img)

    def read_audio(self, file_path: str) -> Any:
        if sf is None:
            return _requires("soundfile")
        data, samplerate = sf.read(file_path)
        duration = float(len(data) / samplerate) if samplerate else 0.0
        return {"samplerate": int(samplerate), "duration": duration, "shape": getattr(data, "shape", None)}

    def read_video(self, file_path: str, max_frames: int = 50) -> Any:
        if cv2 is None:
            return _requires("opencv-python")
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return {"status": "error", "message": "cv2.VideoCapture failed to open"}
        frames = []
        try:
            fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            for _ in range(max_frames):
                ret, frame = cap.read()
                if not ret:
                    break
                frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            duration = (frame_count / fps) if fps else 0.0
            return {"fps": float(fps), "duration": float(duration), "frame_count": frame_count, "frames_sampled": len(frames), "frames": frames}
        finally:
            cap.release()


class _NumpyOnlineSoftmax:
    """Tiny numpy-only online softmax classifier for fallback fine-tuning."""
    def __init__(self, in_dim: int = 256, num_classes: int = 11, lr: float = 1e-2):
        if np is None:
            raise RuntimeError("numpy required for numpy fallback")
        self.in_dim = in_dim
        self.num_classes = num_classes
        self.lr = lr
        self.W = np.zeros((in_dim, num_classes), dtype=np.float32)
        self.b = np.zeros((num_classes,), dtype=np.float32)

    def _softmax(self, z):
        z = z - np.max(z, axis=-1, keepdims=True)
        e = np.exp(z)
        return e / np.sum(e, axis=-1, keepdims=True)

    def step(self, X, y, w):
        # X: (B, D), y: (B,), w: (B,)
        probs = self._softmax(X @ self.W + self.b)
        B = X.shape[0]
        y_one = np.zeros_like(probs)
        y_one[np.arange(B), y] = 1.0
        grad = (probs - y_one) * w[:, None] / max(1, B)
        dW = X.T @ grad
        db = np.sum(grad, axis=0)
        self.W -= self.lr * dW
        self.b -= self.lr * db
        # CE loss
        eps = 1e-9
        loss = -np.sum(w * np.log(probs[np.arange(B), y] + eps)) / max(1, B)
        return float(loss)

    def predict(self, x):
        probs = self._softmax(x @ self.W + self.b)
        return probs


class RealTimeFineTuner:
    """Real-time fine-tuning system (Torch if available; numpy fallback)."""
    def __init__(self, model_path: Optional[str] = None, in_dim: int = 256, num_classes: int = 11):
        self.learning_rate = 1e-3
        self.batch_size = 16
        self.fine_tuning_buffer: List[Dict[str, Any]] = []
        self.lock = threading.Lock()
        self.in_dim = in_dim
        self.num_classes = num_classes

        self._torch_mode = (torch is not None)
        self.model = None
        self.optimizer = None
        self._np_model: Optional[_NumpyOnlineSoftmax] = None

        if self._torch_mode:
            self._init_torch(model_path)
        else:
            if np is not None:
                self._np_model = _NumpyOnlineSoftmax(in_dim=in_dim, num_classes=num_classes, lr=1e-2)

    def _init_torch(self, model_path: Optional[str]):
        assert torch is not None
        if model_path:
            try:
                self.model = torch.load(model_path, map_location="cpu")
                self.model.eval()
            except Exception:
                self.model = None

        if self.model is None:
            self.model = torch.nn.Sequential(
                torch.nn.Linear(self.in_dim, 128),
                torch.nn.ReLU(),
                torch.nn.Linear(128, 64),
                torch.nn.ReLU(),
                torch.nn.Linear(64, self.num_classes),
            )
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)

    def add_training_data(self, input_vec: List[float], target: int, importance: float = 1.0):
        with self.lock:
            self.fine_tuning_buffer.append({
                "input": input_vec,
                "target": int(target),
                "importance": float(importance),
                "timestamp": time.time(),
            })
            if len(self.fine_tuning_buffer) > 1000:
                self.fine_tuning_buffer = self.fine_tuning_buffer[-800:]

    def fine_tune_step(self) -> Dict[str, Any]:
        with self.lock:
            if len(self.fine_tuning_buffer) < self.batch_size:
                return {"status": "insufficient_data", "buffer_size": len(self.fine_tuning_buffer)}

            batch = random.sample(self.fine_tuning_buffer, self.batch_size)
            inputs = [b["input"] for b in batch]
            targets = [b["target"] for b in batch]
            weights = [b["importance"] for b in batch]

        # run outside the lock
        if self._torch_mode and torch is not None:
            X = torch.tensor(inputs, dtype=torch.float32)
            y = torch.tensor(targets, dtype=torch.long)
            w = torch.tensor(weights, dtype=torch.float32)

            assert self.model is not None and self.optimizer is not None
            self.model.train()
            out = self.model(X)
            loss_vec = torch.nn.CrossEntropyLoss(reduction="none")(out, y)
            loss = (loss_vec * w).mean()

            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()

            return {"status": "fine_tuned", "loss": float(loss.item()), "batch_size": self.batch_size, "buffer_size": len(self.fine_tuning_buffer)}

        if self._np_model is not None and np is not None:
            X = np.asarray(inputs, dtype=np.float32)
            y = np.asarray(targets, dtype=np.int64)
            w = np.asarray(weights, dtype=np.float32)
            loss = self._np_model.step(X, y, w)
            return {"status": "fine_tuned", "loss": float(loss), "batch_size": self.batch_size, "buffer_size": len(self.fine_tuning_buffer), "mode": "numpy"}

        return {"status": "unavailable", "message": "No torch or numpy available for fine-tuning"}

    def predict(self, input_vec: List[float]) -> Any:
        if self._torch_mode and torch is not None:
            assert self.model is not None
            with torch.no_grad():
                x = torch.tensor(input_vec, dtype=torch.float32).unsqueeze(0)
                return self.model(x)
        if self._np_model is not None and np is not None:
            x = np.asarray(input_vec, dtype=np.float32)[None, :]
            return self._np_model.predict(x)
        return None


class InformationCoreManager:
    """Main Information Core manager."""
    def __init__(self, core_dir: Optional[str] = None):
        default_root = os.environ.get("GSS1147_ROOT", "X:/gss1147")
        self.core_dir = core_dir or os.path.join(default_root, "information_core")
        self.reader = MultiFormatReader()
        self.fine_tuner = RealTimeFineTuner()

        self.processing_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_size_limit = 1000
        self.stats = {
            "files_processed": 0,
            "formats_supported": len(self.reader.supported_formats),
            "fine_tuning_steps": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }
        os.makedirs(self.core_dir, exist_ok=True)

    # ---- Public API expected by system orchestrator ----
    def process_file(self, file_path: str, enable_fine_tuning: bool = True) -> Dict[str, Any]:
        if file_path in self.processing_cache:
            self.stats["cache_hits"] += 1
            return self.processing_cache[file_path]

        self.stats["cache_misses"] += 1
        read_result = self.reader.read_file(file_path)
        if read_result.get("status") != "success":
            return read_result

        content = read_result.get("content")
        features = self._extract_intelligence_features(content, read_result.get("format", ""))
        if enable_fine_tuning and features and "feature_vector" in features:
            self.fine_tuner.add_training_data(
                features["feature_vector"],
                int(features.get("intelligence_score_bucket", 5)),
                importance=float(features.get("importance", 1.0)),
            )

        result = {
            "status": "success",
            "original_content": content,
            "intelligence_features": features,
            "metadata": read_result,
            "processing_timestamp": datetime.now().isoformat(),
        }
        self.processing_cache[file_path] = result
        self._manage_cache_size()
        self.stats["files_processed"] += 1
        return result

    def enhance_input(self, input_text: str, enable_fine_tuning: bool = True) -> Dict[str, Any]:
        """Enhance a raw text input (no file IO)."""
        features = self._extract_intelligence_features(input_text, ".txt")
        if enable_fine_tuning and features and "feature_vector" in features:
            self.fine_tuner.add_training_data(
                features["feature_vector"],
                int(features.get("intelligence_score_bucket", 5)),
                importance=float(features.get("importance", 1.0)),
            )
        return {"status": "success", "features": features}

    def fine_tune_once(self) -> Dict[str, Any]:
        res = self.fine_tuner.fine_tune_step()
        if res.get("status") == "fine_tuned":
            self.stats["fine_tuning_steps"] += 1
        return res

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self.stats,
            "cache_size": len(self.processing_cache),
            "fine_tuner": {
                "buffer_size": len(self.fine_tuner.fine_tuning_buffer),
                "learning_rate": self.fine_tuner.learning_rate,
                "batch_size": self.fine_tuner.batch_size,
                "mode": "torch" if (torch is not None) else ("numpy" if np is not None else "none"),
            },
            "latest_insights": self.get_intelligence_insights(),
        }

    # ---- Internals ----
    def _extract_intelligence_features(self, content: Any, format_type: str) -> Dict[str, Any]:
        if np is None:
            # minimal fallback without numpy
            return {
                "format_type": format_type,
                "summary": f"numpy not installed; feature extraction is limited for {type(content).__name__}",
                "importance": 0.5,
                "intelligence_score": 5.0,
                "intelligence_score_bucket": 5,
                "feature_vector": [0.0] * 256,
                "format_specific": {},
            }

        features: Dict[str, Any] = {"format_type": format_type}
        if isinstance(content, str):
            words = content.split()
            features["word_count"] = len(words)
            features["unique_words"] = len(set(words))
            features["avg_word_length"] = float(np.mean([len(w) for w in words])) if words else 0.0
            features["sentence_count"] = content.count(".") + content.count("!") + content.count("?")
            features["paragraph_count"] = content.count("\n\n") + 1
            knowledge_words = ["intelligence", "learning", "algorithm", "neural", "recursive", "symbolic", "reasoning", "creativity", "singularity"]
            kd = sum(content.lower().count(w) for w in knowledge_words) / max(1, len(words))
            features["knowledge_density"] = float(kd)

        elif (pd is not None) and isinstance(content, pd.DataFrame):
            features["rows"] = int(len(content))
            features["columns"] = int(len(content.columns))
            features["numeric_columns"] = int(len(content.select_dtypes(include=[np.number]).columns))
            features["categorical_columns"] = int(len(content.select_dtypes(include=["object"]).columns))
            denom = max(1, features["rows"] * features["columns"])
            features["missing_data_ratio"] = float(content.isnull().sum().sum() / denom)

        elif isinstance(content, dict):
            features["key_count"] = int(len(content))
            features["nested_depth"] = int(self._calculate_nested_depth(content))
            features["has_numeric_values"] = bool(any(isinstance(v, (int, float)) for v in content.values()))

        elif isinstance(content, (list, tuple)) and content and isinstance(content[0], dict):
            features["item_count"] = int(len(content))
            features["avg_keys"] = float(np.mean([len(d) for d in content if isinstance(d, dict)]))

        elif np is not None and isinstance(content, np.ndarray):
            features["shape"] = tuple(content.shape)
            features["data_type"] = str(content.dtype)
            features["mean"] = float(np.mean(content))
            features["std"] = float(np.std(content))

        vec = self._content_to_vector(features)
        score = self._calculate_intelligence_score(features, format_type)
        bucket = int(max(0, min(10, round(score))))
        return {
            "feature_vector": vec,
            "intelligence_score": float(score),
            "intelligence_score_bucket": bucket,
            "importance": float(min(1.0, score / 10.0)),
            "format_specific": features,
        }

    def _content_to_vector(self, features: Dict[str, Any]) -> List[float]:
        if np is None:
            return [0.0] * 256

        vec: List[float] = []
        if "word_count" in features:
            vec.extend([features["word_count"] / 1000.0, features["unique_words"] / 1000.0, features.get("knowledge_density", 0.0)])
        elif "rows" in features:
            cols = max(1, features.get("columns", 1))
            vec.extend([features["rows"] / 1000.0, features["columns"] / 100.0, features.get("numeric_columns", 0) / cols])
        elif "mean" in features:
            mean = float(features.get("mean", 0.0))
            std = float(features.get("std", 0.0))
            vec.extend([mean, std / max(1e-6, abs(mean) + 1e-6)])
        elif "key_count" in features:
            vec.extend([features["key_count"] / 100.0, features.get("nested_depth", 0) / 10.0])
        else:
            vec.extend([0.5, 0.5, 0.5])

        # pad/truncate to 256
        if len(vec) < 256:
            vec.extend([0.0] * (256 - len(vec)))
        return vec[:256]

    def _calculate_intelligence_score(self, features: Dict[str, Any], format_type: str) -> float:
        score = 0.0
        if "knowledge_density" in features:
            score += float(features["knowledge_density"]) * 5.0
            score += min(5.0, float(features.get("word_count", 0)) / 1000.0)
        elif "missing_data_ratio" in features:
            score += (1.0 - float(features["missing_data_ratio"])) * 5.0
            score += min(5.0, float(features.get("rows", 0)) / 1000.0)
        elif "std" in features:
            score += abs(float(features["std"])) * 2.0
            score += 3.0
        elif "nested_depth" in features:
            score += float(features.get("nested_depth", 0))
            score += min(5.0, float(features.get("key_count", 0)) / 100.0)
        format_bonus = {".pdf": 2.0, ".json": 3.0, ".csv": 2.5, ".xlsx": 2.5, ".py": 4.0}.get(format_type, 1.0)
        score += format_bonus
        return float(min(10.0, score))

    def _calculate_nested_depth(self, obj: Any, depth: int = 0) -> int:
        if isinstance(obj, dict):
            if not obj:
                return depth
            return max(self._calculate_nested_depth(v, depth + 1) for v in obj.values())
        if isinstance(obj, list) and obj:
            return max(self._calculate_nested_depth(i, depth) for i in obj)
        return depth

    def _manage_cache_size(self):
        if len(self.processing_cache) <= self.cache_size_limit:
            return
        # remove oldest
        items = sorted(self.processing_cache.items(), key=lambda kv: kv[1].get("processing_timestamp", ""))
        for k, _ in items[: max(0, len(self.processing_cache) - self.cache_size_limit + 100)]:
            self.processing_cache.pop(k, None)

    def batch_process_directory(self, directory: str, recursive: bool = True) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        processed = 0
        failed = 0
        it = Path(directory).rglob("*") if recursive else Path(directory).glob("*")
        for p in it:
            if p.is_file() and p.suffix.lower() in self.reader.supported_formats:
                res = self.process_file(str(p))
                results[str(p)] = res
                if res.get("status") == "success":
                    processed += 1
                else:
                    failed += 1
        return {"total_files": len(results), "processed": processed, "failed": failed, "results": results}

    def get_intelligence_insights(self) -> Dict[str, Any]:
        if not self.processing_cache:
            return {"status": "no_data"}
        scores: List[float] = []
        fmt_scores: Dict[str, List[float]] = defaultdict(list)
        opportunities: List[Dict[str, Any]] = []
        for fp, data in self.processing_cache.items():
            feats = data.get("intelligence_features", {})
            if isinstance(feats, dict) and "intelligence_score" in feats:
                s = float(feats["intelligence_score"])
                scores.append(s)
                fmt = data.get("metadata", {}).get("format", "")
                fmt_scores[str(fmt)].append(s)
                if s > 7.0:
                    opportunities.append({"file": fp, "score": s, "reason": "High intelligence content detected"})
        avg = float(sum(scores) / max(1, len(scores)))
        best_fmt = ""
        if fmt_scores:
            best_fmt = max(fmt_scores.keys(), key=lambda k: sum(fmt_scores[k]) / max(1, len(fmt_scores[k])))
        gaps: List[str] = []
        if len(self.processing_cache) < 10:
            gaps.append("Insufficient data for comprehensive analysis")
        if avg < 5.0:
            gaps.append("Low average intelligence score - consider higher quality sources")
        return {
            "total_files_processed": self.stats["files_processed"],
            "average_intelligence_score": avg,
            "most_intelligent_format": best_fmt,
            "learning_opportunities": opportunities[:50],
            "knowledge_gaps": gaps,
        }


    def tick(self, ctx: Dict[str, Any]) -> None:
        """Autonomous micro-step (safe). Computes lightweight insights occasionally."""
        now = float(ctx.get("t", time.time()))
        last = getattr(self, "_last_insight_ts", 0.0)
        if (now - float(last)) >= 120.0:
            try:
                self._last_insight_ts = now
                _ = self.get_intelligence_insights()
            except Exception:
                pass


_info_core_manager: Optional[InformationCoreManager] = None


def get_info_core_manager() -> InformationCoreManager:
    global _info_core_manager
    if _info_core_manager is None:
        _info_core_manager = InformationCoreManager()
    return _info_core_manager


def process_file_intelligently(file_path: str, enable_fine_tuning: bool = True) -> Dict[str, Any]:
    return get_info_core_manager().process_file(file_path, enable_fine_tuning=enable_fine_tuning)


if __name__ == "__main__":  # pragma: no cover
    manager = get_info_core_manager()
    test_file = os.path.join(os.environ.get("GSS1147_ROOT", "X:/gss1147"), "test_data.txt")
    os.makedirs(os.path.dirname(test_file), exist_ok=True)
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("This is a test file about artificial intelligence and recursive learning algorithms.")
    result = process_file_intelligently(test_file)
    print(json.dumps(result, indent=2, default=str))
    print(json.dumps(manager.get_stats(), indent=2, default=str))
import json
import os
import uuid

import folder_paths


MODEL_CACHE = {}
DEFAULT_MODEL_DIR = os.path.join(folder_paths.models_dir, "SenseVoiceSmall")
MODEL_ID = "iic/SenseVoiceSmall"
VAD_MODEL_ID = "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch"
VAD_MODEL_DIR = os.path.join(DEFAULT_MODEL_DIR, "fsmn-vad")


def _import_error_message(error):
    return (
        "SenseVoice dependencies are not installed. Install them in ComfyUI's Python environment:\n"
        "F:\\code\\comfyui\\.ext\\python.exe -m pip install funasr modelscope torchaudio\n"
        f"Original error: {error}"
    )


def _get_device(device):
    if device != "auto":
        return device
    try:
        import torch

        return "cuda:0" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def _resolve_local_model():
    local_model = os.path.abspath(DEFAULT_MODEL_DIR)
    if os.path.isdir(local_model):
        return local_model

    try:
        from modelscope import snapshot_download
    except Exception as e:
        raise RuntimeError(_import_error_message(e))

    os.makedirs(local_model, exist_ok=True)
    print(f"[SenseVoice] Downloading {MODEL_ID} to {local_model}")
    snapshot_download(MODEL_ID, local_dir=local_model)
    if os.path.isdir(local_model):
        return local_model

    raise RuntimeError(
        "SenseVoiceSmall download failed or model folder is not available:\n"
        f"{local_model}"
    )


def _ensure_modelscope_model(model_id, local_dir, label):
    local_dir = os.path.abspath(local_dir)
    if os.path.isdir(local_dir) and os.listdir(local_dir):
        return local_dir

    try:
        from modelscope import snapshot_download
    except Exception as e:
        raise RuntimeError(_import_error_message(e))

    os.makedirs(local_dir, exist_ok=True)
    print(f"[SenseVoice] Downloading {label} to {local_dir}")
    snapshot_download(model_id, local_dir=local_dir)
    return local_dir


def _get_model(vad_model, device):
    local_model = _resolve_local_model()
    local_vad_model = None
    if vad_model and vad_model != "none":
        local_vad_model = _ensure_modelscope_model(VAD_MODEL_ID, VAD_MODEL_DIR, "fsmn-vad")

    cache_key = (local_model, local_vad_model or "none", device)
    if cache_key in MODEL_CACHE:
        return MODEL_CACHE[cache_key]

    try:
        from funasr import AutoModel
        import funasr.utils.install_model_requirements as install_model_requirements
    except Exception as e:
        raise RuntimeError(_import_error_message(e))

    def skip_model_requirements(requirements_path):
        print(f"[SenseVoice] Skip model requirements install: {requirements_path}")
        return True

    install_model_requirements.install_requirements = skip_model_requirements

    kwargs = {
        "model": local_model,
        "device": device,
        "disable_update": True,
    }
    if local_vad_model:
        kwargs["vad_model"] = local_vad_model
        kwargs["vad_kwargs"] = {"max_single_segment_time": 30000}

    model = AutoModel(**kwargs)
    MODEL_CACHE[cache_key] = model
    return model


def _save_audio_to_temp(audio):
    try:
        import torchaudio
    except Exception as e:
        raise RuntimeError(_import_error_message(e))

    if not isinstance(audio, dict) or "waveform" not in audio or "sample_rate" not in audio:
        raise RuntimeError("Invalid ComfyUI AUDIO input.")

    temp_dir = folder_paths.get_temp_directory()
    os.makedirs(temp_dir, exist_ok=True)
    audio_path = os.path.join(temp_dir, f"sensevoice_{uuid.uuid4().hex}.wav")
    waveform = audio["waveform"]
    if waveform.ndim == 3:
        waveform = waveform.squeeze(0)
    torchaudio.save(audio_path, waveform.cpu(), int(audio["sample_rate"]))
    return audio_path


def _seconds_from_any(value):
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if value > 1000:
        value = value / 1000.0
    return max(0.0, value)


def _srt_timestamp(seconds):
    seconds = max(0.0, float(seconds or 0.0))
    total_ms = int(round(seconds * 1000))
    hours, remainder = divmod(total_ms, 3600 * 1000)
    minutes, remainder = divmod(remainder, 60 * 1000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def _append_srt_entry(entries, text, start, end):
    text = str(text or "").strip()
    start = _seconds_from_any(start)
    end = _seconds_from_any(end)
    if not text or start is None or end is None:
        return
    if end <= start:
        end = start + 0.5
    entries.append((start, end, text))


def _first_present(item, *keys):
    for key in keys:
        if key in item and item[key] is not None:
            return item[key]
    return None


def _collect_srt_entries_from_item(item, entries):
    if not isinstance(item, dict):
        return

    sentence_info = item.get("sentence_info")
    if isinstance(sentence_info, list):
        for sentence in sentence_info:
            if not isinstance(sentence, dict):
                continue
            _append_srt_entry(
                entries,
                sentence.get("text"),
                _first_present(sentence, "start", "start_time"),
                _first_present(sentence, "end", "end_time"),
            )

    timestamps = item.get("timestamp")
    if isinstance(timestamps, list):
        for chunk in timestamps:
            if not isinstance(chunk, (list, tuple)) or len(chunk) < 2:
                continue
            text = chunk[2] if len(chunk) > 2 else item.get("text")
            _append_srt_entry(entries, text, chunk[0], chunk[1])


def _build_srt(result):
    items = result if isinstance(result, list) else [result]
    entries = []
    for item in items:
        _collect_srt_entries_from_item(item, entries)

    entries.sort(key=lambda entry: (entry[0], entry[1]))
    blocks = []
    for index, (start, end, text) in enumerate(entries, start=1):
        blocks.append(
            f"{index}\n"
            f"{_srt_timestamp(start)} --> {_srt_timestamp(end)}\n"
            f"{text}"
        )
    return "\n\n".join(blocks)


def _normalize_result(result):
    if isinstance(result, list):
        items = result
    else:
        items = [result]

    texts = []
    for item in items:
        if isinstance(item, dict):
            text = item.get("text")
            if text is None and isinstance(item.get("sentence_info"), list):
                text = "".join(str(sentence.get("text", "")) for sentence in item["sentence_info"])
            if text is not None:
                texts.append(str(text).strip())
        elif item is not None:
            texts.append(str(item).strip())

    text = "\n".join(part for part in texts if part)
    srt = _build_srt(result)
    raw_json = json.dumps(result, ensure_ascii=False, indent=2, default=str)
    return text, srt, raw_json


class SenseVoiceTranscribeAudio:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("AUDIO",),
                "language": (["auto", "zh", "en", "yue", "ja", "ko", "nospeech"],),
                "device": (["auto", "cuda:0", "cpu"],),
                "use_itn": ("BOOLEAN", {"default": True}),
                "batch_size_s": ("INT", {"default": 60, "min": 1, "max": 600, "step": 1}),
            },
            "optional": {
                "vad_model": (["fsmn-vad", "none"],),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("text", "srt", "raw_json")
    FUNCTION = "transcribe"
    CATEGORY = "SenseVoice"

    def transcribe(self, audio, language, device, use_itn, batch_size_s, vad_model="fsmn-vad"):
        audio_path = _save_audio_to_temp(audio)
        try:
            return SenseVoiceTranscribeFile().transcribe(
                audio_path,
                language,
                device,
                use_itn,
                batch_size_s,
                vad_model,
            )
        finally:
            try:
                os.remove(audio_path)
            except OSError:
                pass


class SenseVoiceTranscribeFile:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio_path": ("STRING", {"default": ""}),
                "language": (["auto", "zh", "en", "yue", "ja", "ko", "nospeech"],),
                "device": (["auto", "cuda:0", "cpu"],),
                "use_itn": ("BOOLEAN", {"default": True}),
                "batch_size_s": ("INT", {"default": 60, "min": 1, "max": 600, "step": 1}),
            },
            "optional": {
                "vad_model": (["fsmn-vad", "none"],),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("text", "srt", "raw_json")
    FUNCTION = "transcribe"
    CATEGORY = "SenseVoice"

    def transcribe(self, audio_path, language, device, use_itn, batch_size_s, vad_model="fsmn-vad"):
        if not audio_path:
            raise RuntimeError("audio_path is empty.")

        audio_path = folder_paths.get_annotated_filepath(audio_path)
        if not os.path.exists(audio_path):
            raise RuntimeError(f"Audio file not found: {audio_path}")

        infer_device = _get_device(device)
        recognizer = _get_model(vad_model, infer_device)
        language_arg = "auto" if language == "auto" else language

        result = recognizer.generate(
            input=audio_path,
            cache={},
            language=language_arg,
            use_itn=bool(use_itn),
            batch_size_s=int(batch_size_s),
            merge_vad=True,
            merge_length_s=15,
        )
        return _normalize_result(result)


NODE_CLASS_MAPPINGS = {
    "SenseVoiceTranscribeAudio": SenseVoiceTranscribeAudio,
    "SenseVoiceTranscribeFile": SenseVoiceTranscribeFile,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SenseVoiceTranscribeAudio": "SenseVoice Transcribe Audio",
    "SenseVoiceTranscribeFile": "SenseVoice Transcribe File",
}

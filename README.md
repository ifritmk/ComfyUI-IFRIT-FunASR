# ComfyUI-SenseVoice

ComfyUI custom nodes for local SenseVoiceSmall speech recognition.

## Nodes

- `SenseVoice Transcribe Audio`
  - Input: ComfyUI `AUDIO`
  - Output: recognized text, SRT, and raw JSON
- `SenseVoice Transcribe File`
  - Input: audio file path
  - Output: recognized text, SRT, and raw JSON

## Model Path

This plugin only uses SenseVoiceSmall.

The model path is fixed to:

```text
F:\code\comfyui\models\SenseVoiceSmall
```

The UI does not expose a model selector. If the folder does not exist, the plugin downloads:

```text
iic/SenseVoiceSmall
```

to the fixed local folder above.

When `vad_model` is `fsmn-vad`, the VAD model is also kept under the same model folder:

```text
F:\code\comfyui\models\SenseVoiceSmall\fsmn-vad
```

The plugin downloads `iic/speech_fsmn_vad_zh-cn-16k-common-pytorch` to that folder when needed.

## Dependencies

Install dependencies in ComfyUI's Python environment:

```powershell
F:\code\comfyui\.ext\python.exe -m pip install funasr modelscope torchaudio
```

The plugin skips FunASR's per-model `requirements.txt` auto-install step at runtime so it does not spawn `pip` while ComfyUI is running.

## Inputs

- `language`: `auto`, `zh`, `en`, `yue`, `ja`, `ko`, `nospeech`
- `device`: `auto`, `cuda:0`, `cpu`
- `use_itn`: inverse text normalization
- `batch_size_s`: inference batch size in seconds
- `vad_model`: `fsmn-vad` or `none`

## Outputs

- `text`: merged recognized text
- `srt`: subtitle text in SRT format when timestamps are available
- `raw_json`: raw FunASR result JSON

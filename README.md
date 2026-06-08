# ComfyUI FunASR

这是一个 ComfyUI 自定义节点插件，用于调用 FunASR 做语音识别，并在模型返回真实时间戳时输出 SRT 字幕。

## 节点

- `FunASR Transcribe Audio`
  - 输入：ComfyUI `AUDIO`
  - 输出：识别文本、SRT 字幕
- `FunASR Transcribe File`
  - 输入：音频文件路径
  - 输出：识别文本、SRT 字幕

## 模型选择

节点的 `model` 下拉框包含：

```text
Paraformer-Large
SenseVoiceSmall
```

`Paraformer-Large` 适合中文识别和时间戳/SRT 输出。

`SenseVoiceSmall` 适合语音识别、情感标签和事件标签。如果需要说话人标签，可以启用 `spk_model=cam++`。

## 本地模型目录

模型固定放在 ComfyUI 的 `models` 目录下：

```text
F:\code\comfyui\models\Paraformer-Large
F:\code\comfyui\models\SenseVoiceSmall
```

如果目录不存在，节点会把选中的模型下载到对应固定目录。

启用 `vad_model=fsmn-vad` 时，VAD 模型会放在：

```text
F:\code\comfyui\models\Paraformer-Large\fsmn-vad
F:\code\comfyui\models\SenseVoiceSmall\fsmn-vad
```

启用 `punc_model=ct-punc` 或 `spk_model=cam++` 时，辅助模型会放在当前主模型目录下：

```text
F:\code\comfyui\models\Paraformer-Large\ct-punc
F:\code\comfyui\models\Paraformer-Large\cam++
F:\code\comfyui\models\SenseVoiceSmall\ct-punc
F:\code\comfyui\models\SenseVoiceSmall\cam++
```

离线部署时，请提前把上述模型目录放好。

## 依赖

在 ComfyUI 的 Python 环境中安装依赖：

```powershell
F:\code\comfyui\.ext\python.exe -m pip install funasr huggingface_hub modelscope transformers torchaudio
```

建议使用较新的 FunASR 版本。当前节点按 FunASR 1.3.x 的返回结构适配。

节点运行时会跳过 FunASR 模型目录里的 `requirements.txt` 自动安装步骤，避免 ComfyUI 运行过程中额外拉起 pip。

## 输入参数

- `model`：选择 `Paraformer-Large` 或 `SenseVoiceSmall`
- `language`：语言，支持 `auto`、`zh`、`en`、`yue`、`ja`、`ko`、`nospeech`
- `device`：推理设备，支持 `auto`、`cuda:0`、`cpu`
- `use_itn`：是否启用逆文本归一化
- `batch_size_s`：推理批处理时长，单位秒
- `vad_model`：选择 `fsmn-vad` 或 `none`
- `punc_model`：选择 `ct-punc` 或 `none`
- `spk_model`：选择 `cam++` 或 `none`

## 输出

- `text`：合并后的识别文本
- `srt`：SRT 字幕文本

SRT 只会在 FunASR 返回真实时间戳时生成。节点会读取以下字段：

```text
sentence_info
timestamp
timestamps
ctc_timestamps
```

如果模型没有返回真实时间戳，`srt` 会为空，不会用音频总时长硬切假字幕。

## 使用建议

中文字幕优先使用：

```text
model=Paraformer-Large
vad_model=fsmn-vad
punc_model=ct-punc
spk_model=none
```

需要说话人标签时再开启：

```text
spk_model=cam++
```

如果只想要 SenseVoice 的情感/事件标签，可以使用：

```text
model=SenseVoiceSmall
vad_model=fsmn-vad
punc_model=none
spk_model=none
```

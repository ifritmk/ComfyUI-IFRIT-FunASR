# ComfyUI IFRIT FunASR

这是一个 ComfyUI 自定义节点插件，用 FunASR 做语音识别和字幕生成。

## 节点

### FunASR Text

- 输入：ComfyUI `AUDIO`
- 输出：`text`
- 固定使用：`models\SenseVoiceSmall`

这个节点只负责生成识别文本，不生成 SRT。

长音频会使用 `fsmn-vad` 分段识别，避免整段音频一次性进入 SenseVoiceSmall 导致显存峰值过高。

### FunASR SRT

- 输入：ComfyUI `AUDIO`
- 输出：`srt`
- 文本模型：`models\SenseVoiceSmall`
- 时间戳模型：`models\Paraformer-Large`

这个节点会先用 SenseVoiceSmall 生成文本，再用 Paraformer-Large 返回的真实时间戳生成 SRT。不会按音频总时长平均切假字幕。

SRT 文本会按 SenseVoiceSmall 返回的标点拆成多条字幕，再贴到 Paraformer-Large 的时间轴上。逗号、句号、问号、感叹号都会分段；SRT 输出会去掉标点。

对齐时会先把 SenseVoiceSmall 文本和 Paraformer-Large 文本都转成纯文字，再用相似度生成位置对照表；每个 SenseVoice 字幕段会通过这张表找到对应的 Paraformer token 时间戳范围。

## 模型目录

模型固定放在 ComfyUI 的 `models` 目录：

```text
F:\code\comfyui\models\SenseVoiceSmall
F:\code\comfyui\models\Paraformer-Large
```

如果目录不存在，节点会把模型下载到对应固定目录。离线部署时请提前放好这些目录。

Paraformer-Large 会额外使用 VAD 模型，目录为：

```text
F:\code\comfyui\models\Paraformer-Large\fsmn-vad
F:\code\comfyui\models\SenseVoiceSmall\fsmn-vad
```

## 输入参数

- `audio`：ComfyUI 音频对象。
- `device`：推理设备，支持 `auto`、`cuda:0`、`cpu`。
- `batch_size_s`：FunASR 推理分段参数，单位秒。
- `unload_model`：任务结束后是否释放当前节点加载的缓存模型。

节点里没有 `model` 参数。Text 节点固定 SenseVoiceSmall，SRT 节点固定 SenseVoiceSmall + Paraformer-Large。

`FunASR SRT` 会在 SenseVoiceSmall 识别完成后立刻释放它，再加载 Paraformer-Large 生成时间轴，避免长音频同时占用两个 ASR 模型的显存。SRT 节点的 `unload_model` 默认开启。

## 依赖

在 ComfyUI 的 Python 环境中安装：

```powershell
F:\code\comfyui\.ext\python.exe -m pip install funasr modelscope huggingface_hub transformers torchaudio
```

建议使用 FunASR 1.3.x 或更新版本。

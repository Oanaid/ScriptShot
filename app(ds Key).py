import streamlit as st
import json
import csv
import io
import os

# ── 页面配置 ──
st.set_page_config(
    page_title="ScriptShot - 剧本智能分镜",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 自定义样式 ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700&display=swap');

html, body, [class*="st-"] {
    font-family: 'Noto Sans SC', sans-serif;
}
.main-title {
    font-size: 2.4rem;
    font-weight: 700;
    color: #1a1a2e;
    margin-bottom: 0;
    letter-spacing: -0.5px;
}
.sub-title {
    font-size: 1.05rem;
    color: #666;
    margin-top: 4px;
    margin-bottom: 2rem;
}
.scene-header {
    background: linear-gradient(135deg, #f0c27f, #e8a849);
    color: #333;
    padding: 8px 16px;
    border-radius: 6px;
    font-weight: 600;
    font-size: 0.95rem;
    margin: 20px 0 10px 0;
}
.stat-box {
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 8px;
    padding: 16px;
    text-align: center;
}
.stat-number {
    font-size: 1.8rem;
    font-weight: 700;
    color: #1a1a2e;
}
.stat-label {
    font-size: 0.8rem;
    color: #888;
    margin-top: 4px;
}
div[data-testid="stDataFrame"] table {
    font-size: 0.85rem;
}
.stAlert {
    border-radius: 8px;
}
[data-testid="stFileUploader"] button {
    visibility: hidden;
}
[data-testid="stFileUploader"] button::after {
    content: "点击上传文件";
    visibility: visible;
    display: block;
}
</style>
""", unsafe_allow_html=True)

# ── 分镜生成 Prompt ──
SYSTEM_PROMPT = """你是一位资深导演和摄影指导，擅长将剧本转化为专业的分镜头脚本。

## 任务
根据用户提供的剧本内容和风格要求，生成完整的分镜表。

## 输出格式
输出一个 JSON 对象，包含两个字段：
{
  "memo": "全局创作备忘（200字以内，包含故事主题、情绪曲线、风格建议、声音设计方向）",
  "scenes": [
    {
      "scene_header": "场景一：日外 英国公园",
      "shots": [
        {
          "shot_id": 1,
          "shot_size": "中景",
          "angle": "斜侧、平拍",
          "movement": "固定镜头",
          "action": "男主和女主坐在长椅上，男主悠闲地吃着三明治",
          "dialogue": "男主：你要实在想回中国，你就拿着护照买张机票就好啦。",
          "duration": "4s",
          "note": "音乐比较轻快愉悦"
        }
      ]
    }
  ]
}

## 字段取值规范

### 景别 shot_size（8选1）
大远景 / 远景 / 全景 / 中景 / 中近景 / 近景 / 特写 / 大特写
特殊：黑场（用于情绪极端转折、梦境/现实切换）

### 角度 angle（方位+俯仰合写）
方位：正面 / 斜侧 / 侧面 / 背面 / 过肩
俯仰：平拍 / 仰拍 / 俯拍
格式："斜侧、平拍" "过肩、俯拍" "正面、仰拍"

### 镜头运动 movement（10选1）
固定镜头 / 推镜头 / 拉镜头 / 摇镜头 / 移镜头 / 跟焦镜头 / 升降镜头 / 手持镜头 / 空镜头 / 虚焦镜头

### 画面内容 action
- 不超过30字，只写画面中发生的事
- 禁止使用：电影感、震撼、史诗、唯美、氛围感、高级感、有张力

### 台词 dialogue（三种格式）
- 出声台词："角色名：台词"
- 内心独白："角色名内心：台词"
- 画外音："角色名（画外音）：台词"
- 无台词时填 ""

### 时长 duration
格式"数字+s"，如 "3s" "0.5s" "7s"，支持0.5s精度

### 备注 note
五类信息：
- 音乐提示："音乐比较轻快愉悦" "音乐淡出"
- 音效："音效：相机快门声"
- 台词延留："每个镜头间台词有延留"
- 剪辑手法："同一镜头跳剪" "此处两个镜头来回切换"
- 转场/视角："1/2动作转场" "女主视角"
- 无则填 ""

## 生成规则

1. 生成每个镜头前先思考：与上一镜的衔接、景别跳跃是否合理、是否越轴、声音变化
2. 每场戏开头通常需要建立镜头
3. 对话场景注意180°轴线
4. 主动标注音乐进出、音效、转场手法
5. 对白归属必须准确
6. 画外音和内心独白要正确区分
7. 输出纯JSON，不要任何额外文字"""

STYLE_RULES = {
    "古典叙事": """风格：古典叙事
- 景别过渡平滑，不从大特写直跳大远景
- 严格180°轴线
- 对话用经典正反打
- 镜头时长3-8s，节奏稳健
- 转场以硬切为主""",
    "纪实手持": """风格：纪实手持
- 手持跟拍为主，自然光
- 中近景偏多
- 允许轻微晃动感
- 镜头时长3-10s
- 少设计感机位，追求真实感""",
    "东亚长镜头": """风格：东亚长镜头
- 长时长固定镜头（5-15s）
- 全景和中景为主，极少特写
- 大量留白
- 极简转场
- 情绪驱动而非情节驱动""",
    "短视频叙事": """风格：短视频叙事
- 允许跳剪，同一机位拆短镜头，标注"同一镜头跳剪"
- 允许景别快速跳跃
- 允许积累蒙太奇
- 允许0.5s超短镜头
- 画外音旁白推动叙事
- 音乐音效重度参与
- 镜头时长1-4s，高密度""",
    "快节奏剪辑": """风格：快节奏剪辑
- 短镜头（0.5-3s）
- 景别频繁变化
- 运镜丰富
- 动作转场
- 节奏紧凑，信息密度高""",
}

# ── 辅助函数 ──

def extract_text_from_file(uploaded_file):
    """从上传的文件中提取文本"""
    name = uploaded_file.name.lower()
    if name.endswith('.txt'):
        return uploaded_file.read().decode('utf-8')
    elif name.endswith('.docx'):
        try:
            import docx
            doc = docx.Document(io.BytesIO(uploaded_file.read()))
            return '\n'.join([p.text for p in doc.paragraphs if p.text.strip()])
        except ImportError:
            st.error("需要安装 python-docx：pip install python-docx")
            return None
    elif name.endswith('.pdf'):
        try:
            import pdfplumber
            text_parts = []
            with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        text_parts.append(t)
            return '\n'.join(text_parts)
        except ImportError:
            st.error("需要安装 pdfplumber：pip install pdfplumber")
            return None
    else:
        st.error("不支持的文件格式，请上传 .txt / .docx / .pdf")
        return None


def call_llm(script_text, style, mode, api_key, provider):
    """调用 LLM API 生成分镜（支持 Claude / DeepSeek / 通义千问）"""

    style_rule = STYLE_RULES.get(style, "")
    mode_rule = ""
    if mode == "关键镜头":
        mode_rule = "\n\n## 输出模式：关键镜头\n只输出每个场景中最关键的镜头（建立镜头、情绪转折点、高潮镜头、转场镜头），每场3-6个镜头即可。"

    user_msg = f"""## 风格要求
{style_rule}
{mode_rule}

## 剧本内容
{script_text}"""

    if provider == "Claude":
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = message.content[0].text
    else:
        # DeepSeek / 通义千问 —— 都兼容 OpenAI 格式
        from openai import OpenAI
        if provider == "DeepSeek":
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
            model = "deepseek-chat"
        elif provider == "通义千问":
            client = OpenAI(api_key=api_key, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
            model = "qwen-max"
        else:
            raise ValueError(f"未知的模型提供商：{provider}")

        response = client.chat.completions.create(
            model=model,
            max_tokens=8000,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.7,
        )
        raw = response.choices[0].message.content

    # 清理可能的 markdown 包裹
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    return json.loads(raw)


def generate_html_export(result, style):
    """生成 HTML 分镜表"""
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>ScriptShot 分镜表</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;600;700&display=swap');
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Noto Sans SC', sans-serif; padding: 20px; background: #fff; color: #333; }}
h1 {{ font-size: 1.4rem; text-align: center; margin-bottom: 4px; }}
.meta {{ text-align: center; color: #888; font-size: 0.8rem; margin-bottom: 20px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
th {{ background: #1a1a2e; color: #fff; padding: 8px 6px; text-align: left; font-weight: 600; }}
td {{ padding: 7px 6px; border-bottom: 1px solid #e0e0e0; vertical-align: top; }}
tr:nth-child(even) td {{ background: #f8f9fa; }}
.scene-row td {{ background: linear-gradient(135deg, #f0c27f, #e8a849) !important; font-weight: 600; color: #333; padding: 10px 6px; }}
.memo {{ background: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 6px; padding: 12px; margin-bottom: 20px; font-size: 0.85rem; line-height: 1.6; }}
.memo-title {{ font-weight: 600; margin-bottom: 6px; }}
@media print {{
  body {{ padding: 10px; }}
  @page {{ size: A4 landscape; margin: 10mm; }}
  table {{ page-break-inside: auto; }}
  tr {{ page-break-inside: avoid; }}
}}
</style>
</head>
<body>
<h1>ScriptShot 分镜表</h1>
<div class="meta">风格：{style} ｜ 由 ScriptShot AI 生成</div>
"""
    if result.get("memo"):
        html += f'<div class="memo"><div class="memo-title">创作备忘</div>{result["memo"]}</div>'

    html += """<table>
<tr><th style="width:4%">镜号</th><th style="width:7%">景别</th><th style="width:9%">角度</th><th style="width:9%">镜头运动</th><th style="width:25%">画面内容</th><th style="width:25%">台词</th><th style="width:5%">时长</th><th style="width:12%">备注</th><th style="width:4%">参考画面</th></tr>
"""
    for scene in result.get("scenes", []):
        header = scene.get("scene_header", "")
        html += f'<tr class="scene-row"><td colspan="9">{header}</td></tr>\n'
        for shot in scene.get("shots", []):
            html += f"""<tr>
<td>{shot.get('shot_id','')}</td>
<td>{shot.get('shot_size','')}</td>
<td>{shot.get('angle','')}</td>
<td>{shot.get('movement','')}</td>
<td>{shot.get('action','')}</td>
<td>{shot.get('dialogue','')}</td>
<td>{shot.get('duration','')}</td>
<td>{shot.get('note','')}</td>
<td></td>
</tr>\n"""

    html += "</table></body></html>"
    return html


def generate_csv_export(result):
    """生成 CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["镜号","景别","角度","镜头运动","画面内容","台词","时长","备注","参考画面"])
    for scene in result.get("scenes", []):
        writer.writerow([scene.get("scene_header",""), "", "", "", "", "", "", "", ""])
        for shot in scene.get("shots", []):
            writer.writerow([
                shot.get("shot_id",""), shot.get("shot_size",""), shot.get("angle",""),
                shot.get("movement",""), shot.get("action",""), shot.get("dialogue",""),
                shot.get("duration",""), shot.get("note",""), ""
            ])
    return output.getvalue()


# ── 侧边栏 ──
with st.sidebar:
    st.markdown("### ⚙️ 设置")

    provider = st.selectbox(
        "🤖 模型提供商",
        ["DeepSeek", "Claude", "通义千问"],
        help="DeepSeek：中国可用，便宜好用｜Claude：需美区账号｜通义千问：阿里云",
    )

    provider_hints = {
        "DeepSeek": ("在 platform.deepseek.com 获取", "sk-..."),
        "Claude": ("在 console.anthropic.com 获取", "sk-ant-..."),
        "通义千问": ("在 dashscope.console.aliyun.com 获取", "sk-..."),
    }
    hint, placeholder = provider_hints[provider]

    api_key = st.text_input(
        f"{provider} API Key",
        type="password",
        placeholder=placeholder,
        help=hint,
        value=os.environ.get("ANTHROPIC_API_KEY", "") if provider == "Claude" else "",
    )

    st.markdown("---")
    style = st.selectbox(
        "🎨 分镜风格",
        ["短视频叙事", "古典叙事", "纪实手持", "东亚长镜头", "快节奏剪辑"],
        help="不同风格对应不同的镜头逻辑和剪辑规则",
    )

    mode = st.radio(
        "📋 输出模式",
        ["完整分镜", "关键镜头"],
        help="完整分镜列出所有镜头；关键镜头只列出每场戏的核心镜头",
    )

    st.markdown("---")
    st.markdown("""
    <div style="font-size: 0.75rem; color: #999; line-height: 1.5;">
    <b>ScriptShot</b> 是一款面向影视创作者的 AI 分镜工具。<br><br>
    上传剧本 → 选择风格 → 一键生成专业分镜表。<br><br>
    支持景别、角度、运镜、台词（含画外音/内心独白）、声音设计等专业标注。
    </div>
    """, unsafe_allow_html=True)


# ── 主区域 ──
st.markdown('<div class="main-title">🎬 ScriptShot</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">上传剧本，AI 自动生成专业分镜表</div>', unsafe_allow_html=True)

# 输入方式
tab_upload, tab_paste = st.tabs(["📁 上传文件", "📝 粘贴文本"])

script_text = None

with tab_upload:
    uploaded = st.file_uploader(
        "支持 .txt / .docx / .pdf",
        type=["txt", "docx", "pdf"],
        help="上传你的剧本文件",
    )
    if uploaded:
        script_text = extract_text_from_file(uploaded)
        if script_text:
            with st.expander("📖 查看提取的文本", expanded=False):
                st.text(script_text[:3000] + ("..." if len(script_text) > 3000 else ""))

with tab_paste:
    pasted = st.text_area(
        "粘贴剧本文本",
        height=300,
        placeholder="将你的剧本内容粘贴到这里...",
    )
    if pasted.strip():
        script_text = pasted.strip()

# 生成按钮
st.markdown("")
col_btn, col_info = st.columns([1, 3])
with col_btn:
    generate = st.button("🎬 生成分镜", type="primary", use_container_width=True, disabled=not script_text or not api_key)
with col_info:
    if not api_key:
        st.caption("⚠️ 请在左侧填入 Claude API Key")
    elif not script_text:
        st.caption("⚠️ 请先上传剧本或粘贴文本")
    else:
        st.caption(f"✅ 就绪 ｜ 风格：{style} ｜ 模式：{mode}")

# ── 生成逻辑 ──
if generate and script_text and api_key:
    with st.spinner("🎬 正在生成分镜表，请稍候（约 30-60 秒）..."):
        try:
            result = call_llm(script_text, style, mode, api_key, provider)
            st.session_state["result"] = result
            st.session_state["style"] = style
        except json.JSONDecodeError:
            st.error("⚠️ AI 返回的格式有误，请重试")
        except Exception as e:
            err = str(e)
            if "authentication" in err.lower():
                st.error("⚠️ API Key 无效，请检查")
            elif "rate" in err.lower():
                st.error("⚠️ API 调用频率超限，请等待 60 秒后重试")
            else:
                st.error(f"⚠️ 生成失败：{err}")

# ── 展示结果 ──
if "result" in st.session_state:
    result = st.session_state["result"]
    used_style = st.session_state.get("style", style)

    # 统计
    total_shots = sum(len(s.get("shots", [])) for s in result.get("scenes", []))
    total_scenes = len(result.get("scenes", []))
    total_duration = 0
    for scene in result.get("scenes", []):
        for shot in scene.get("shots", []):
            d = shot.get("duration", "0s").replace("s", "")
            try:
                total_duration += float(d)
            except ValueError:
                pass

    st.markdown("---")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="stat-box"><div class="stat-number">{total_scenes}</div><div class="stat-label">场景数</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-box"><div class="stat-number">{total_shots}</div><div class="stat-label">镜头数</div></div>', unsafe_allow_html=True)
    with c3:
        mins = int(total_duration // 60)
        secs = int(total_duration % 60)
        dur_str = f"{mins}分{secs}秒" if mins > 0 else f"{secs}秒"
        st.markdown(f'<div class="stat-box"><div class="stat-number">{dur_str}</div><div class="stat-label">预估总时长</div></div>', unsafe_allow_html=True)

    # 创作备忘
    if result.get("memo"):
        with st.expander("📝 创作备忘", expanded=False):
            st.write(result["memo"])

    # 分镜表
    st.markdown("### 📋 分镜表")

    for scene in result.get("scenes", []):
        header = scene.get("scene_header", "未知场景")
        st.markdown(f'<div class="scene-header">{header}</div>', unsafe_allow_html=True)

        shots = scene.get("shots", [])
        if shots:
            import pandas as pd
            df = pd.DataFrame(shots)
            column_map = {
                "shot_id": "镜号", "shot_size": "景别", "angle": "角度",
                "movement": "镜头运动", "action": "画面内容", "dialogue": "台词",
                "duration": "时长", "note": "备注"
            }
            df = df.rename(columns={k: v for k, v in column_map.items() if k in df.columns})
            display_cols = ["镜号","景别","角度","镜头运动","画面内容","台词","时长","备注"]
            display_cols = [c for c in display_cols if c in df.columns]
            st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

    # 导出
    st.markdown("---")
    st.markdown("### 📥 导出")
    col_csv, col_html, col_json = st.columns(3)

    with col_csv:
        csv_data = generate_csv_export(result)
        st.download_button("下载 CSV", csv_data, "storyboard.csv", "text/csv", use_container_width=True)

    with col_html:
        html_data = generate_html_export(result, used_style)
        st.download_button("下载 HTML", html_data, "storyboard.html", "text/html", use_container_width=True)

    with col_json:
        json_data = json.dumps(result, ensure_ascii=False, indent=2)
        st.download_button("下载 JSON", json_data, "storyboard.json", "application/json", use_container_width=True)

# VoiceAgent - 园区来客电话 AI Agent

一个基于：

- Twilio 电话系统
- Deepgram 实时语音识别（STT）
- Groq LLM
- FastAPI WebSocket
- 企业微信 Webhook

构建的中文实时电话 Agent。

系统支持：

- AI 电话访客登记
- 老访客记忆
- 中文车牌纠错
- 门卫电话查询
- 企业微信自动推送
- 多 Agent 路由
- 实时语音流处理

---

# 项目背景

传统园区来客登记通常依赖：

- 人工电话登记
- 纸质登记
- 微信人工沟通
- 保安手动查询

流程繁琐，效率低。

本项目尝试使用：

```text
实时语音 AI + LLM Agent
```

实现：

```text
电话自动接待
→ 自然语言对话
→ 信息结构化
→ 自动推送
→ 历史记录查询
```

形成完整的 AI 门岗登记系统。

---

# 核心功能

## 1. AI 电话访客登记

访客拨打电话后：

- Agent 自动接听
- 中文自然语言对话
- 自动采集信息
- 自动确认登记
- 自动推送企业微信

支持采集：

- 车牌号
- 来访单位
- 来访事由
- 来电手机号

示例：

```text
用户：
浙A12345，去蓝色鲸鱼科技送货。

Agent：
我确认一下，
车牌号浙A12345，
来访单位蓝色鲸鱼科技，
来访事由送货，对吗？
```

---

## 2. 老访客记忆

系统会根据：

```text
来电手机号
```

自动识别历史访客。

例如：

```text
我查到您之前登记的信息是：
车牌号浙A12345，
来访单位蓝色鲸鱼科技，
来访事由送货。
请问这次还是这些信息吗？
```

用户可以：

```text
是
```

直接复用历史信息。

也可以：

```text
不是
```

重新修改本次登记。

---

## 3. 中文车牌纠错

系统支持中文语音车牌纠错，例如：

```text
浙江A12345 → 浙A12345
折A12345 → 浙A12345
这A12345 → 浙A12345
```

以及数字纠错：

```text
洞 → 0
幺 → 1
两 → 2
```

采用：

```text
规则匹配 + LLM 修复
```

双层方案。

---

## 4. 门卫查询 Agent

指定门卫号码拨打电话后：

系统会自动进入：

```text
guard_query_agent
```

门卫可以直接通过自然语言查询来访记录。

例如：

```text
今天来了多少人？
```

```text
下午三点到五点来了多少人？
```

```text
浙A12345 来过几次？
```

```text
蓝色鲸鱼科技今天来了多少人？
```

```text
最近五条访客记录是什么？
```

```text
今天有哪些车牌？
```

系统会：

```text
自然语言问题
→ LLM 生成查询计划
→ 查询 visitor_records.jsonl
→ LLM 生成自然语言回复
```
---

## 5. 企业微信自动推送

登记完成后：

系统会自动向企业微信群发送结构化通知。

示例：

```text
【园区来客登记】

车牌号：浙A12345
来访单位：蓝色鲸鱼科技
手机号：13800138000
来访事由：送货
入场时间：2026-05-25 10:30:00
```

---

# 系统架构

```text
用户电话
   ↓
Twilio 接听
   ↓
Twilio Media Stream
   ↓
FastAPI WebSocket
   ↓
Deepgram Streaming STT
   ↓
身份识别（手机号）
   ├── VisitorRegistrationAgent
   └── GuardQueryAgent
   ↓
Groq LLM
   ↓
JSON 数据
   ↓
企业微信 / 语音回复
```

---

# 项目结构

```text
.
├── main.py                    # FastAPI 主入口
├── registration_agent.py      # 访客登记 Agent
├── guard_query_agent.py       # 门卫查询 Agent
├── visitor_record_query.py    # 来访记录查询
├── guard_config.py            # 门卫号码配置
├── stt_deepgram.py            # Deepgram 实时 STT
├── llm_groq.py                # Groq API 封装
├── correction_engine.py       # 中文纠错 / 车牌纠错
├── intent_utils.py            # 用户意图识别
├── memory_store.py            # 老访客记忆
├── wechat_sender.py           # 企业微信推送
├── schemas.py                 # 数据结构
├── config.py                  # 环境变量
├── visitor_memory.json        # 历史访客记忆
├── visitor_records.jsonl      # 来访记录
├── requirements.txt
└── README.md
```

---

# 项目亮点

## 1. 实时电话 AI Agent

不是普通聊天机器人，而是：

```text
电话实时语音 Agent
```

涉及：

- Twilio 实时音频流
- WebSocket
- 流式 STT
- 实时对话状态管理

---

## 2. 多 Agent 架构

系统支持：

```text
普通访客
→ VisitorRegistrationAgent

门卫
→ GuardQueryAgent
```

通过：

```text
手机号自动路由
```

实现不同 Agent 的自动切换。

---

## 3. 流式语音识别

采用：

```text
Deepgram Streaming STT
```

支持：

- 实时识别
- endpointing
- VAD
- 中文电话音频

---

## 4. Session 隔离与状态管理

系统实现：

```text
visitor:{call_sid}
guard:{call_sid}
```

隔离不同 Agent session。

支持：

- session cleanup
- 通话结束自动清理
- 防止状态复用
- 防止 Agent 串话

---

# 安装依赖

```bash
pip install -r requirements.txt
```

---

# 环境变量

创建 `.env`：

```env
PUBLIC_HOST=

DEEPGRAM_API_KEY=

GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile

TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=

WECHAT_WEBHOOK=

GUARD_PHONE_NUMBERS=
```

---

# 启动方式

## 1. 启动 FastAPI

```bash
uvicorn main:app --host 0.0.0.0 --port 80
```

## 2. 启动 ngrok

```bash
ngrok http 80
```

## 3. 配置 Twilio Webhook

```text
https://你的ngrok域名/voice
```

---

# 数据存储

## visitor_memory.json

保存：

- 老访客信息
- 公司词库
- 来访事由词库

示例：

```json
{
  "visitors": {
    "13800138000": {
      "plate_number": "浙A12345",
      "target_company": "蓝色鲸鱼科技",
      "phone": "13800138000",
      "last_visit_reason": "送货"
    }
  }
}
```

---

## visitor_records.jsonl

保存每一次真实登记记录。

示例：

```json
{"plate_number":"浙A12345","target_company":"蓝色鲸鱼科技","phone":"13800138000","visit_reason":"送货","entry_time":"2026-05-25 10:30:00"}
```

门卫查询 Agent 查询的就是该文件。

---

# 当前已实现能力

- 中文实时电话对话
- Deepgram 实时 STT
- Groq LLM 信息抽取
- 老访客记忆
- 中文车牌纠错
- 多轮对话
- 门卫查询 Agent
- 企业微信推送
- session 隔离
- session cleanup
- WebSocket 双流
- 自然语言查询 visitor records

---

# Demo 示例

## 访客登记

```text
用户：
浙A12345，去蓝色鲸鱼科技送货。

Agent：
我确认一下，
车牌号浙A12345，
来访单位蓝色鲸鱼科技，
来访事由送货，对吗？
```

---

## 门卫查询

```text
门卫：
今天来了多少人？

Agent：
今天共有 12 条来访记录。
```

---

# License

MIT License
# 🏥 AI Healthcare Assistant Chatbot

🚀 **Live Demo:** https://tracynguyen01-ai-healthcare-assistant-app-qi6ci3.streamlit.app/  
👉 Try: *"How to reduce fever at home?"*

---

## 💡 What is this?

An **AI-powered healthcare chatbot** that uses **RAG (Retrieval-Augmented Generation)** to deliver **more reliable, structured, and safer health information**.

Unlike typical chatbots, this system:
- Retrieves real medical context  
- Validates generated answers  
- Outputs structured responses  

👉 Built as a **production-style AI system**, not just a demo.

---

## ⚡ Why this project stands out

- 🧠 **Hybrid RAG Pipeline** (internal + external retrieval)
- 🔎 **Real-time search integration** (Tavily)
- 🧩 **Robust JSON parsing & validation**
- 🛡️ **Safety + answer critic layer**
- 🌐 **Fully deployed app** (Streamlit)

---

## 🧠 How it works (simplified)

```text
User Query
   ↓
Query Planning (intent + expansion)
   ↓
Hybrid Retrieval
   ├─ Internal (FAISS vector DB)
   └─ External (Web search)
   ↓
Context Filtering & Ranking
   ↓
LLM Generation (Groq)
   ↓
Safety Check + Answer Critic
   ↓
Structured Response (JSON → UI)
```
---

## 🏗️ System Highlights

This project simulates a real-world AI system pipeline:

* Data crawling from medical sources
* Text preprocessing + chunking
* Embedding + FAISS vector storage
* Hybrid retrieval (internal + external)
* Query planning & fallback search
* LLM generation with structured outputs
* Safety filtering & hallucination mitigation
* 
---
## 📊 Dashboard Preview
<details>
  <summary>Click to expand</summary>
  <br/>
  <p align="center">
    <img src="assert/ai_healthcare_assistant.png" width="900"/>
  </p>
</details>

---
## 🛠️ Tech Stack

<p align="left">

- <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original.svg" width="25"/> Python 
- <img src="https://streamlit.io/images/brand/streamlit-logo-secondary-colormark-darktext.png" width="25"/> Streamlit 
- 🤖 LLM APIs (Groq / OpenAI)  
- 🔎 Tavily Search API  
- 🧩 JSON Parsing & Validation 

</p>

---
## 🧩 Challenges & Solutions

| Challenge           | Solution                     |
| ------------------- | ---------------------------- |
| LLM hallucination   | Hybrid retrieval (RAG)       |
| Weak context        | Query planning + expansion   |
| No/low results      | Fallback search pipeline     |
| Unstructured output | JSON parsing + validation    |
| Safety risks        | Answer critic + safety layer |

---
## 🚀 Run Locally
```bash
git clone https://github.com/tracynguyen01/ai-healthcare-assistant
cd ai-healthcare-assistant

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```
Create .env:
```bash
GROQ_API_KEY=your_key
TAVILY_API_KEY=your_key
```
Run:
```bash
streamlit run app.py
```
---
## 🔮 Future Improvements
* Full vector database optimization
* Medical knowledge base integration
* User personalization
* Multi-language support
* Cloud deployment (AWS/GCP)
* 
---
## ⚠️ Disclaimer
This project is for educational purposes only and does not replace professional medical advice.

---
## 👩‍💻 Author
**Ngoc Bao Tran (Tracy) Nguyen**

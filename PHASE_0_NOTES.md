# DocForge — Phase 0: Complete Beginner-Friendly Guide & Notes
*(Zero to Hero: Python, Backend & RAG Architecture Basics in Simple Hinglish)*

> **Target Audience:** Python me absolute beginner, first major software engineering project, aur interview preparation.  
> **Rule:** Koi bhi ratta nahi marna hai. Har ek line of code, command, aur folder ke piche ka "KYU" (WHY) aur "KAISE" (HOW) samajhna hai.

---

## Table of Contents
1. [DocForge Kya Hai? (Big Picture & Problem Statement)](#1-docforge-kya-hai)
2. [Folder Structure — Hamne Aise Folder Kyu Banaye?](#2-folder-structure)
3. [Virtual Environment (.venv) & Python Runtimes — Ground Zero Concept](#3-virtual-environment)
4. [Ek-Ek Command Ka Post-Mortem (Hamne Kya Run Kiya Aur Internally Kya Hua?)](#4-commands-post-mortem)
5. [Har Ek File Ka Deep-Dive (Line-by-Line Code Breakdown & Real-Life Analogies)](#5-file-by-file-breakdown)
   - [5.1 `.gitignore`](#51-gitignore)
   - [5.2 `.env.example`](#52-envexample)
   - [5.3 `README.md`](#53-readmemd)
   - [5.4 `backend/pyproject.toml`](#54-backendpyprojecttoml)
   - [5.5 `backend/src/docforge/__init__.py`](#55-backendsrcdocforge__init__py)
   - [5.6 `backend/src/docforge/domain/`, `adapters/`, `api/`, `workers/`](#56-architecture-packages)
   - [5.7 `backend/src/docforge/config/__init__.py`](#57-config-__init__py)
   - [5.8 `backend/src/docforge/config/settings.py` (Super Important!)](#58-configsettingspy)
   - [5.9 `backend/src/docforge/config/logging.py`](#59-configloggingpy)
   - [5.10 Test Files (`test_smoke.py`, `test_settings.py`, `test_logging.py`)](#510-test-files)
   - [5.11 Placeholder Files (`.gitkeep`)](#511-placeholder-gitkeep-files)
   - [5.12 `frontend/` (Vite + React + TypeScript Scaffold)](#512-frontend-scaffold)
6. [Core Technical Terms Dictionary (Beginner-Friendly Definitions)](#6-technical-dictionary)
7. [Phase 0 Ka Current Status: Kya Ho Gaya Aur Kya Baki Hai?](#7-current-status)
8. [Interview Q&A: Interviewer Ke Samne Kaise Explain Karoge?](#8-interview-qa)

---

<a name="1-docforge-kya-hai"></a>
## 1. DocForge Kya Hai? (Big Picture & Problem Statement)

### 📌 Simple Definition:
**DocForge ek Multi-User PDF Question-Answering (RAG) System hai.**  
Iska matlab: User apne PDFs (reports, legal documents, textbooks, research papers) upload karega, aur AI se natural English me sawal puchega. AI us document ko padhkar accurate jawab dega — **aur sabse zaruri baat: jawab ke sath page number aur exact sentence/region ka reference (Citation) dega.**

### 🛑 Real-World Problem: "ChatGPT Se PDF Padhwana Kafi Kyu Nahi Hai?"
1. **Hallucination (Jhoot bolna):** Normal AI agar answer nahi janta, toh confident lagne wala jhoota answer fabricate kar deta hai.
2. **Missing Source (Hawala na hona):** Agar AI ne koi number bola (jaise "Company revenue grew by 18%"), toh aap verify kaise karoge ki wo PDF ke page 42 pe sach me likha hai ya AI ne man se banaya?
3. **Large Files Limit:** Ek 500-page ka manual direct prompt me nahi daala ja sakta.
4. **Privacy Issue:** Companies apna confidential PDF public server pe bina authorization ke nahi bhej sakti.

### 💡 DocForge Ka Solution (RAG Engine):
DocForge **RAG (Retrieval-Augmented Generation)** use karta hai:
- Pehle PDF ko analyze karke chote-chote readable pieces (**Chunks**) me todta hai.
- Chunks ko mathematically search-ready banata hai (**Embeddings & Full-Text Search**).
- Jab user question puchta hai, toh DocForge sabse pehle **sirf relevant passages** dhoondhta hai.
- Fir AI (Gemini) ko bolta hai: *"Sirf inhi passages me se answer do, agar answer passages me nahi hai toh saaf mana kar do (Abstain karo), jhoot mat bolo!"*
- UI me user jab citation click karta hai, toh built-in PDF viewer khul jata hai aur exact page aur sentence highlight ho jata hai.

---

<a name="2-folder-structure"></a>
## 2. Folder Structure — Hamne Aise Folder Kyu Banaye?

Hamara project layout aisa dikhta hai:

```text
DocForge/
├── .github/
│   └── workflows/
│       └── .gitkeep            <-- Future CI/CD pipelines (Phase 11)
├── backend/                    <-- Saara Python Backend Code
│   ├── alembic/                <-- Database migrations (Phase 2)
│   ├── src/
│   │   └── docforge/           <-- Main Application Package
│   │       ├── domain/         <-- Business logic (Pure Python, no frameworks)
│   │       ├── adapters/       <-- External services (Database, Gemini AI, S3/R2 storage)
│   │       ├── api/            <-- Web routes (FastAPI endpoints)
│   │       ├── workers/        <-- Background heavy tasks (Celery queue)
│   │       └── config/         <-- Settings & Logging
│   ├── tests/                  <-- Automated pytest suite
│   └── pyproject.toml          <-- Python dependencies & build config
├── frontend/                   <-- React + Vite + TypeScript UI
├── evaluation/                 <-- Benchmark PDFs & QA dataset (Phase 1)
├── .env.example                <-- Secrets configuration template
├── .gitignore                  <-- Files jo Git me save nahi karni
├── architecture.md             <-- System architecture specification
├── design.md                   <-- UI/UX specification
├── memory.md                   <-- Live project state & progress
├── phases.md                   <-- 13-phase implementation roadmap
├── prd.md                      <-- Product requirements document
├── rules.md                    <-- Development guidelines & standards
└── README.md                   <-- Project overview
```

### 🧠 Clean Architecture (Hexagonal / Ports-and-Adapters) Concept:
Dhyan se dekho `backend/src/docforge/` ke andar 4 alag folders hain:
1. **`domain/` (Core Logic):** Isme pure rules honge — jaise "Chunk kya hota hai?", "Citation valid kab maani jayegi?". Is folder me koi FastAPI ya SQL database ka code nahi hoga. Ye bilkul pure Python code hota hai.
2. **`adapters/` (Plug-and-Play Tools):** Kal ko agar hum database badal kar Postgres se kuch aur karein ya Cloudflare R2 ki jagah AWS S3 use karein, toh sirf adapter badlega, main logic (`domain`) nahi badlega.
3. **`api/` (Door to Outside World):** Yaha FastAPI ke endpoints honge jo frontend se requests receive karenge.
4. **`workers/` (Laborers):** PDF parse karna aur embed karna time-consuming kaam hai (10-20 seconds lag sakte hain). Agar API ye sab khud karegi toh user ka browser wait karte karte freeze ho jayega. Isliye API request leke turant return kar deti hai, aur heavy kaam `workers` (Celery) ko de deti hai jo background me chalte hain.

---

<a name="3-virtual-environment"></a>
## 3. Virtual Environment (.venv) & Python Runtimes — Ground Zero Concept

### ❓ Virtual Environment Kya Hai?
**Real-life Analogy:**  
Maan lo aapke paas ek kitchen hai (Aapka pura Laptop). Ek dish ko banane ke liye Mirchi powder 1.0 chahiye, doosri dish ko banane ke liye Mirchi powder 2.0 chahiye. Agar aap pure kitchen me global masala daal doge, toh ek dish banegi aur doosri kharab ho jayegi.  
**Virtual Environment** aapke project ka ek chota private kitchen cabinet hai! Isme jo packages install honge wo sirf DocForge ke andar rahenge, aapke computer ke baaki projects ko disturb nahi karenge.

### ❓ Hamne `.venv` Kyu Banaya?
Jab hum `pip install pydantic` karte hain:
- Agar virtual environment active **nahi** hai: Python library aapke C Drive ke Global Windows folder me chali jati hai.
- Agar virtual environment active **hai**: Library sirf `DocForge/.venv/Lib/site-packages/` me install hoti hai.
- Jab project delete karna ho ya naye computer pe clone karna ho, toh clean state rehti hai.

---

<a name="4-commands-post-mortem"></a>
## 4. Ek-Ek Command Ka Post-Mortem

Humne jo commands run kiye, unka ek-ek shabd aur internal mechanism samajhte hain:

---

### Command 1: `git status` aur `git init`

```powershell
git init
```
- **What it does:** Isne `DocForge/` folder ke andar ek hidden folder `.git/` create kar diya.
- **Internally:** Git ne ek local database bana diya jo har file ke changes ka hisaab (history/snapshots) rakhega.

```powershell
git checkout -b phase-0-foundation
```
- **`git checkout`:** Branch switch karne ka command.
- **`-b`:** "New Branch" create karo agar exist nahi karti.
- **`phase-0-foundation`:** Branch ka naam.
- **Internally:** Humne `master` branch ko chhod kar ek safe development branch bana li, taaki sara Phase 0 ka kaam isolated rahe.

---

### Command 2: Hardware Detection Script (`get_hw.ps1`)

Humne PowerShell me script chalayi hardware janne ke liye:
```powershell
Get-CimInstance Win32_OperatingSystem
Get-CimInstance Win32_Processor
Get-CimInstance Win32_ComputerSystem
```
- **What happened:** CIM (Common Information Model) Windows ka ek built-in system management API hai jo CPU, RAM aur Disk ki physical jankari deta hai.
- **Result:**
  - **OS:** Windows 11 Pro
  - **CPU:** Intel Core i7-10610U (4 Cores, 8 Logical Processors)
  - **RAM:** ~16 GB (15.78 GB total, ~5.9 GB free)
  - **Disk Free:** ~38.2 GB
- **Why this matters for DocForge:** Free Render cloud hosting pe sirf **512 MB RAM** milti hai! Local machine pe 16GB hai, par cloud pe memory bohot kam hogi. Isliye hume worker concurrency (ek sath kitne PDF process honge) ko 1 ya 2 tak hi rakhna padega, warna server memory crash (OOM - Out of Memory) ho jayega.

---

### Command 3: `python -m venv .venv`

```powershell
python -m venv .venv
```
- **`python`:** Python executable ko call kiya.
- **`-m` (Module flag):** Python ko bola ki ek built-in library/module run karo jiska naam `venv` hai.
- **`.venv`:** Us folder ka naam jaha virtual environment banega (dot aage lagane se ye convention wise hidden/special folder mana jata hai).
- **Internally:** Is command ne `.venv/` folder banaya, uske andar Python interpreter ka ek private copy/link rakha, aur `Scripts/pip.exe` create kiya.

---

### Command 4: `.\.venv\Scripts\pip.exe install -e "backend[dev]"`

Ye command bohot important hai, isko dhyan se samjho:

```powershell
.\.venv\Scripts\pip.exe install -e "backend[dev]"
```
- **`.\.venv\Scripts\pip.exe`:** Hum global computer ka pip use nahi kar rahe! Hum virtual environment ke andar wale private `pip.exe` ko direct call kar rahe hain.
- **`install`:** Package install karne ka instruction.
- **`-e` (Editable Mode):** Ye magical flag hai! Iska matlab: `docforge` backend ko as a library install karo, lekin compile karke bundle mat banao. Jab bhi hum `backend/src/docforge/` ke kisi file me change karenge, bina dobara `pip install` kiye wo changes turant reflect ho jayenge.
- **`backend`:** Folder ka path jaha `pyproject.toml` rakha hai.
- **`[dev]`:** `pyproject.toml` ke andar jo optional `dev` group hai (jisme `pytest`, `ruff` hain), unko bhi sath me install karo.

**Internally Kya Hua?**
1. Pip ne `backend/pyproject.toml` ko padha.
2. Pata lagaya ki project ko `pydantic`, `pydantic-settings`, `pytest`, `pytest-asyncio`, aur `ruff` chahiye.
3. Internet (PyPI - Python Package Index) se un packages ke `.whl` (Wheel files) download kiye.
4. Unhe `.venv\Lib\site-packages\` me place kar diya.
5. Ek pointer file banayi jisse Python ko pata chale ki `import docforge` karne pe `backend/src/docforge` ko load karna hai.

---

### Command 5: `.\.venv\Scripts\pytest.exe backend\tests`

```powershell
.\.venv\Scripts\pytest.exe backend\tests
```
- **`pytest.exe`:** Python ka standard testing framework runner.
- **`backend\tests`:** Pytest ko bataya ki kis folder me test files dhoondhni hain.
- **Internally:**
  1. Pytest ne `backend/tests` me `test_*.py` pattern wali saari files dhoondhi.
  2. Unke andar `def test_*():` wale functions ko execute kiya.
  3. Dekha ki koi `assert` statement fail toh nahi hui.
  4. Sabhi 4 tests pass ho gaye (**4 passed in 3.85s**).

---

### Command 6: `npm create vite@latest frontend -- --template react-ts`

```powershell
npm create vite@latest frontend -- --template react-ts
```
- **`npm`:** Node Package Manager (JavaScript/Web ecosystem ka pip).
- **`create vite@latest`:** Vite ek ultra-fast modern frontend build tool hai (React projects start karne ka modern tareeka).
- **`frontend`:** Folder ka naam jisme code generate hoga.
- **`-- --template react-ts`:** Template batayi: **React** framework use karo with **TypeScript** (Typed JavaScript).

---

<a name="5-file-by-file-breakdown"></a>
## 5. Har Ek File Ka Deep-Dive (Line-by-Line Code Breakdown & Real-Life Analogies)

Aao ab har ek file ko inspect karte hain jo Phase 0 me bani hai.

---

<a name="51-gitignore"></a>
### 5.1 `.gitignore`

#### 📄 Kya hai ye file?
Git version control ke liye ek blacklist file hai. Isme likhi hui koi bhi file ya folder Git me commit (save/upload) nahi hota.

#### 💡 Real-Life Analogy:
Jab aap airport pe security check se guzarate ho, toh airport authority ke paas ek list hoti hai: "Lighter, Scissors, Liquids allowed nahi hain". `.gitignore` wahi security check hai: "Passwords, heavy junk files, aur private PDFs GitHub pe nahi jayenge!"

#### 🔍 Code Analysis:
```gitignore
# Environment & Secrets
.env
.env.local
*.key
*.pem
```
👉 **Kyu:** `.env` me real database passwords aur Gemini API keys hoti hain. Agar galti se ye GitHub pe chali gayi, toh koi bhi aapka cloud balance khatam kar sakta hai ya data chura sakta hai.

```gitignore
# Python & Virtual Environments
.venv/
__pycache__/
*.py[cod]
```
👉 **Kyu:** `.venv` 500MB se 1GB ka ho sakta hai aur har operating system ke liye alag hota hai (Windows ka `.venv` Linux pe nahi chalta). Isliye isko Git me dalna bekar hai. `__pycache__` Python ka compiled bytecode hota hai (`.pyc`), jo computer khud banata hai.

```gitignore
# Documents & Data (Preserve privacy)
*.pdf
*.PDF
evaluation/corpus/*.pdf
```
👉 **Kyu (Very Important for DocForge):** DocForge ka prime directive hai: **Privacy by default.** User ke PDFs ya hamare evaluation PDFs kabhi bhi code repository me public nahi hone chahiye.

---

<a name="52-envexample"></a>
### 5.2 `.env.example`

#### 📄 Kya hai ye file?
Ye ek sample template hai jo developer ko batata hai ki project chalane ke liye kaun-kaun se environment variables (secrets/keys) chahiye. Isme dummy/fake values hoti hain.

#### 💡 Real-Life Analogy:
Ek blank form ya application sample: jisme likha hota hai `Name: [Enter Name Here]`, `Account No: [00000000]`. Aap is sample ko dekh kar apna real form bharte ho.

#### 🔍 Code Analysis:
```ini
ENVIRONMENT=development
LOG_LEVEL=INFO
APP_NAME=DocForge

DATABASE_URL=postgresql://user:password@ep-sample-123456.us-east-2.aws.neon.tech/docforge?sslmode=require
SECRET_KEY=replace-with-a-secure-random-secret-key-for-jwt-signing
GEMINI_API_KEY=AIzaSySampleKeyDoNotCommitRealSecrets
```
- `DATABASE_URL`: Neon cloud PostgreSQL database ka connection string.
- `SECRET_KEY`: User ke login sessions (JWT tokens) ko digitally sign karne ke liye encryption key.
- `GEMINI_API_KEY`: Google AI Studio se milne wali API key.

---

<a name="53-readmemd"></a>
### 5.3 `README.md`

#### 📄 Kya hai ye file?
Project ka front page / face. Jab koi GitHub pe project kholega, toh sabse pehle ye file render hoti hai. Isme DocForge ka introduction aur core specification files ke clickable links hain.

---

<a name="54-backendpyprojecttoml"></a>
### 5.4 `backend/pyproject.toml`

#### 📄 Kya hai ye file?
Modern Python ka **Single Source of Truth** for configuration & dependencies. Purane time me log `requirements.txt`, `setup.py`, `setup.cfg`, `pytest.ini` alag-alag banate the. Modern Python me sab kuch **ek hi file** me standard format me rehta hai: `pyproject.toml`.

#### 💡 Real-Life Analogy:
Aapke restaurant ka Official Menu Card aur Recipe Book. Isme likha hai chef kaun hai, dish ka naam kya hai, aur kaunse masale (libraries) khareedne padenge.

#### 🔍 Code Analysis Line-by-Line:

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"
```
👉 **Line-by-line:**
- `[build-system]`: Python packaging tools (jaise pip) ko batata hai ki is project ko install karne ke liye kaun sa builder software use karna hai.
- `setuptools` aur `wheel`: Wo standard packaging engines hain jo Python code ko installable module me convert karte hain.

```toml
[project]
name = "docforge-backend"
version = "0.1.0"
description = "DocForge backend service: multi-user PDF RAG application"
requires-python = ">=3.11"
```
👉 **Line-by-line:**
- Project ka internal package name aur version.
- `requires-python = ">=3.11"`: Ye enforce karta hai ki agar koi Python 3.10 ya purana version use karega toh pip error de dega. (DocForge modern Python features use karta hai).

```toml
dependencies = [
    "pydantic>=2.7.0",
    "pydantic-settings>=2.2.0",
]
```
👉 **Line-by-line:**
- **`pydantic`:** Python ka sabse popular Data Validation tool. Ye ensure karta hai ki data ka type sahi ho.
- **`pydantic-settings`:** Environment variables (`.env`) ko type-safe tareeqe se load karne ki modern library.

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.4.0",
]
```
👉 **Line-by-line:**
- Ye wo tools hain jo production server pe nahi chahiye, sirf developers ko coding aur testing ke time chahiye.
- `pytest`: Tests run karne ke liye.
- `pytest-asyncio`: Asynchronous (`async def`) functions ko test karne ke liye.
- `ruff`: Code ko clean rakhne aur styling formatting check karne ke liye (fastest linter in Python).

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-v --strict-markers"
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
```
👉 **Line-by-line:**
- `testpaths = ["tests"]`: Pytest ko bataya ki tests sirf `tests` folder me khojo.
- `pythonpath = ["src"]`: **Very Important!** Iske bina jab test file me aap `import docforge` likhoge toh Python ko samajh nahi aayega ki `docforge` kaha hai. Ye line `src/` folder ko Python path me jod deti hai.
- `addopts = "-v"`: Verbose mode (har test ka naam screen pe detail me dikhao).

---

<a name="55-backendsrcdocforge__init__py"></a>
### 5.5 `backend/src/docforge/__init__.py`

#### 📄 Kya hai ye file?
Ek Python package initializer.
#### 🔍 Code:
```python
"""DocForge core package."""

__version__ = "0.1.0"
```
#### ❓ Python me `__init__.py` kyu hota hai?
Jab kisi folder me `__init__.py` file hoti hai, toh Python us folder ko ek ordinary folder nahi manta, balki ek **importable package** manta hai. Iske bina aap doosri files me `from docforge import ...` nahi likh sakte.

---

<a name="56-architecture-packages"></a>
### 5.6 `domain/`, `adapters/`, `api/`, `workers/` packages

Hamne in chaaron folders ke andar ek-ek clean `__init__.py` banaya:
- `docforge.domain`: Pure business rules (chunks, citations, evaluation score math).
- `docforge.adapters`: Third-party integrations (Postgres, Gemini API, R2 Storage).
- `docforge.api`: FastAPI routers aur request/response validation schemas.
- `docforge.workers`: Celery background tasks jo heavy PDF parsing karenge.

Ye Phase 0 me **placeholders** hain — inka core architecture tayar hai, implementation aage ke phases me aayegi.

---

<a name="57-config-__init__py"></a>
### 5.7 `backend/src/docforge/config/__init__.py`

#### 🔍 Code:
```python
"""Configuration and application composition root."""

from docforge.config.settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]
```
#### ❓ `__all__` kya hota hai?
Jab doosri file likhegi: `from docforge.config import *`, toh sirf wo cheezein export hongi jo `__all__` list ke andar hain. Ye Python ka clean code standard hai.

---

<a name="58-configsettingspy"></a>
### 5.8 `backend/src/docforge/config/settings.py` (Super Important!)

#### 📄 Kya hai ye file?
Application ka central control room. Saare passwords, database URLs, AI model names yaha defined hain.

#### 💡 Real-Life Analogy:
Aapke TV ka remote control aur settings menu. Channel ka connection kaisa hoga, volume limit kya hogi — sab ek jagah configured rehta hai.

#### 🔍 Code Analysis Line-by-Line:

```python
from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
```
👉 **Terms:**
- `from functools import lru_cache`: "Least Recently Used" Cache. Ek performance trick hai. Settings ko baar-baar hard drive ya `.env` se read nahi karna padega; memory me ek baar load karke cache kar lega.
- `Literal`: Strict values restrict karne ke liye (jaise `ENVIRONMENT` sirf 4 values me se ek ho sakti hai).
- `BaseSettings`: Pydantic ka magic class jo automatically computer ke environment variables ko scan karta hai aur Python variables me convert karta hai.

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )
```
👉 **Line-by-line:**
- `env_file=".env"`: Pydantic ko bola: "Agar system me variable nahi mile, toh project ke `.env` file me se dhoondh lo."
- `extra="ignore"`: Agar `.env` me koi aisi line hai jo humne code me define nahi ki, toh crash mat hona, ignore kar dena.
- `case_sensitive=False`: `log_level` aur `LOG_LEVEL` dono ko same samjho.

```python
    ENVIRONMENT: Literal["development", "staging", "production", "test"] = "development"
    LOG_LEVEL: str = "INFO"
    APP_NAME: str = "DocForge"

    DATABASE_URL: str = "postgresql://localhost:5432/docforge"
    SECRET_KEY: str = "insecure-dev-secret-key-replace-in-production-before-deploy"
```
👉 **How this works:**
Maan lo computer pe koi setting nahi set ki gayi hai, toh automatically default value use hogi (`development`, `INFO`, `postgresql://localhost:5432/docforge`).  
Lekin jaise hi hum cloud pe deploy karenge aur waha environment variable denge:  
`DATABASE_URL=postgresql://real_user:real_pass@neon.tech/db`,  
toh Pydantic bina code change kiye apne aap real value pick kar lega! **Isko kehte hain Twelve-Factor App Principle.**

```python
@lru_cache
def get_settings() -> Settings:
    return Settings()
```
👉 **Why `@lru_cache`?**
Agar hamare app pe 1,000 users ek sath aate hain, hum nahi chahte ki 1,000 baar `.env` file disk se read ho. `@lru_cache` se ye function sirf pehli call pe run hoga, aur baki 999 baar wahi saved instance return kar dega. Ultra-fast!

---

<a name="59-configloggingpy"></a>
### 5.9 `backend/src/docforge/config/logging.py`

#### 📄 Kya hai ye file?
Server ke andar kya chal raha hai, usko record karne ka system (Blackbox recorder).

#### 🛑 Normal `print()` Kyu Nahi Use Karte?
Beginners aksar `print("User logged in")` likhte hain. Lekin professional backend me `print()` use karna mana hota hai, kyu ki:
1. `print()` me timestamp (kis waqt hua) nahi hota.
2. `print()` me log level (Warning, Error, Info) nahi hota.
3. Cloud platforms (Render, Datadog, CloudWatch) normal text ko search nahi kar pate. Unhe **JSON format** chahiye hota hai.

#### 🔍 Code Analysis:

```python
class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_payload, default=str)
```
👉 **How it works:**  
Jab bhi hum log karenge: `logger.info("PDF upload started")`, toh terminal pe aisi sundar structured JSON line print hogi:
```json
{"timestamp": "2026-11-06T17:32:00.123456Z", "level": "INFO", "logger": "docforge.api", "message": "PDF upload started"}
```

#### 🔒 Security Rule (DocForge Directive):
Humne architecture rule banaya hai: **Kabhi bhi logs ke andar user ka password, signed URL, ya PDF ka private text print nahi hoga.**

---

<a name="510-test-files"></a>
### 5.10 Test Files (`backend/tests/`)

Automated tests wo code hota hai jo hamare application code ko verify karta hai ki wo sahi kaam kar raha hai ya nahi.

#### 1. `test_smoke.py`:
```python
def test_smoke() -> None:
    assert docforge.__version__ == "0.1.0"
```
- **"Smoke Test" Term Kaha Se Aaya?**  
  Purane zamane me electronics hardware repairing me circuit board ko power on karke dekhte the ki "dhuaan (smoke) toh nahi nikal raha?". Agar dhuaan nahi nikla, toh basic circuit theek hai.  
  Software me Smoke Test ka matlab: Project import ho raha hai aur crash nahi ho raha.

#### 2. `test_settings.py`:
```python
def test_default_settings() -> None:
    settings = Settings()
    assert settings.APP_NAME == "DocForge"

def test_env_override(monkeypatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    settings = Settings()
    assert settings.LOG_LEVEL == "DEBUG"
```
- **`monkeypatch` Kya Hai?**  
  Pytest ka ek built-in tool hai. Ye test chalte waqt temporary environment variable inject karta hai aur test khatam hote hi computer ko wapas pehle jaisa clean kar deta hai. Isse humne test kiya ki agar user `.env` me value badlega toh setting sach me override hoti hai ya nahi.

#### 3. `test_logging.py`:
```python
def test_json_formatter() -> None:
    # Ek fake log record banaya aur check kiya ki kya json.loads() bina error ke parse ho raha hai
```
- Ye verify karta hai ki JSON formatter valid JSON generate kar raha hai.

---

<a name="511-placeholder-gitkeep-files"></a>
### 5.11 Placeholder Files (`.gitkeep`)

#### ❓ `.gitkeep` Kya Hai?
Git ka ek rule hota hai: **Git khali (empty) folders ko track nahi karta.**  
Agar aap `evaluation/` naam ka empty folder banaoge, toh wo Git commit me aayega hi nahi.  
Isliye developers ek empty file rakh dete hain jiska naam convention wise `.gitkeep` rakha jata hai, taaki Git us folder ko save kar le.

Hamne banayi:
- `backend/alembic/.gitkeep` (Phase 2 Database Migrations ke liye)
- `evaluation/.gitkeep` (Phase 1 Benchmark Dataset ke liye)
- `.github/workflows/.gitkeep` (Phase 11 CI/CD automation ke liye)

---

<a name="512-frontend-scaffold"></a>
### 5.12 `frontend/` (Vite + React + TypeScript Scaffold)

`npm create vite@latest frontend -- --template react-ts` ne ek standard React + TypeScript project banaya:
- `frontend/package.json`: Frontend ki dependencies list (React 19, TypeScript, Vite).
- `frontend/vite.config.ts`: Vite server config.
- `frontend/src/main.tsx`: React ka entry file jaha se UI start hoti hai.
- `frontend/src/App.tsx`: Main screen component (Phase 8 me hum yaha apna PDF viewer aur QA panel banayenge).

---

<a name="6-technical-dictionary"></a>
## 6. Core Technical Terms Dictionary (Beginner-Friendly Definitions)

| Term | Simple Meaning |
|---|---|
| **RAG (Retrieval-Augmented Generation)** | AI ko pehle relevant document dhoondh ke dena, fir bolna ki is document ke aadhar par answer likho. |
| **Virtual Environment (`.venv`)** | Project ka private library folder taaki system ke baaki projects disturb na hon. |
| **Dependencies** | Wo third-party open-source libraries jo hamare code ko chalne ke liye chahiye hoti hain (jaise `pydantic`, `pytest`). |
| **Editable Install (`pip install -e`)** | Code me changes karte hi bina reinstall kiye instant test karne ki facility. |
| **Type Hints (`str`, `int`, `Literal`)** | Python me variables ke sath unka type likhna taaki bugs code run hone se pehle hi pakad me aa jayein. |
| **LRU Cache (`@lru_cache`)** | Function ke result ko memory me yaad rakhna taaki baar-baar mehenga kaam na karna pade. |
| **Fixture (Pytest)** | Test run hone se pehle setup karne wala helper tool (jaise `monkeypatch`). |
| **Pydantic** | Python ka gatekeeper jo incoming data ko check karta hai ki wo valid format me hai ya nahi. |
| **Hinglish Analogy: Ingestion** | PDF ko kholna, uske tukde karna aur database me save karna. |

---

<a name="7-current-status"></a>
## 7. Phase 0 Ka Current Status: Kya Ho Gaya Aur Kya Baki Hai?

Hamein transparent aur honest rehna hai rules ke mutabiq:

### ✅ Jo Complete Ho Chuka Hai (Implemented & Tested):
1. **Repository & Git Setup:** Git initialize hua, `.gitignore` banaya gaya, aur `phase-0-foundation` branch banayi gayi.
2. **Hardware Facts Collected:** OS (Windows 11), CPU (i7 4-core), RAM (16GB), Disk (38GB free) record kiya gaya.
3. **Python Runtime & Dependencies:** Python 3.11.9 detect hua, `.venv` virtual environment create kiya gaya, aur `pyproject.toml` se `pydantic-settings`, `pytest` install hue.
4. **Clean Project Structure:** `domain`, `adapters`, `api`, `workers`, `config` folders organize hue.
5. **Modern Settings & Structured Logging:** Pydantic-settings aur JSON logging implement hui.
6. **Passing Test Suite:** 4 out of 4 pytest unit tests pass hue.
7. **Frontend Scaffolding:** Vite + React + TypeScript base structure create hua.
8. **Six Specification Files Preserved:** Architecture, PRD, Rules, Design, Phases, Memory files safe hain bina kisi overwrite ke.

### ⏳ Jo Phase 0 Me Abhi Baki Hai (Pending Next Steps):
1. **External Providers Verification (Documentation Feasibility):**
   - Neon PostgreSQL (pgvector support & free limits)
   - Render Web Service & Key Value / Valkey (sleep limits & memory limits)
   - Neon Object Storage vs Cloudflare R2 (signed URLs & HTTP Range requests)
   - Vercel (frontend limits)
   - Google Gemini API (exact model IDs: `text-embedding-004`, `gemini-2.0-flash`, quotas, pricing)
2. **Updating `memory.md`:** Verification ke results aur hardware specs ko `memory.md` me record karna.

---

<a name="8-interview-qa"></a>
## 8. Interview Q&A: Interviewer Ke Samne Kaise Explain Karoge?

Jab aap interview me baithe honge, toh ye questions aapse puche ja sakte hain:

### Q1: "Aapne `requirements.txt` ki jagah `pyproject.toml` kyu use kiya?"
> **Your Answer:**  
> *"Sir, PEP 518 aur PEP 621 ke mutabiq modern Python standards me `pyproject.toml` standard ban chuka hai. Purane approaches me hume dependencies ke liye `requirements.txt`, packaging ke liye `setup.py`, aur testing ke liye `pytest.ini` alag maintain karni padti thi jisse version drift hota tha. `pyproject.toml` single source of truth provide karta hai jaha build system, dependencies, dev-tools, aur pytest configuration ek hi declarative file me rehti hai."*

### Q2: "Aapne Pydantic v1 BaseSettings ki jagah `pydantic-settings` kyu use kiya?"
> **Your Answer:**  
> *"In Pydantic V2, `BaseSettings` ko core library se alag karke `pydantic-settings` package me modularize kar diya gaya hai. Hamne modern `SettingsConfigDict` use kiya hai jo `.env` parsing, case-insensitivity, aur strict type-checking handle karta hai without polluting the core data models."*

### Q3: "Render Free Tier pe Celery aur FastAPI ek sath chalana safe hai?"
> **Your Answer:**  
> *"Render ke free tier pe 512MB RAM milti hai. Agar Celery aur FastAPI same instance me chalenge, toh heavy PDF parsing ke time memory spike aa sakta hai. Isliye humne Phase 0 me hi decide kiya hai ki worker concurrency ko strictly bound (1-2 workers) rakhenge aur task payloads me raw PDF bytes pass nahi karenge, sirf document IDs pass karenge."*

### Q4: "DocForge me Local Evidence Mode aur Cloud AI Mode me kya farak hai?"
> **Your Answer:**  
> *"DocForge privacy-first architecture follow karta hai. Default state 'local-only' hoti hai jaha documents kabhi Gemini API pe nahi jaate. User local full-text search aur PDF view kar sakta hai. Jab user explicitly 'cloud-allowed' consent deta hai, tabhi hamara EgressGate outbound calls permit karta hai for semantic embeddings aur AI generation."*

---

*(In notes ko acche se read karo. Ye aapka foundational knowledge base hai. Jab aap bolenge, hum aage ke verification steps ko execute karke Phase 0 complete karenge!)*


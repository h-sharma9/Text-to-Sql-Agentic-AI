# 🤖 Agentic Text-to-SQL & Document RAG Engine — Complete Project Overview

---

## 1. What Is This Project About?

### The Problem Statement

Every modern e-commerce company sits on two types of knowledge:

1. **Structured Data** — Millions of rows in databases: orders, customers, products, payments, reviews, delivery logs. To get answers from this data ("What was our top-selling category last quarter?"), you need to know SQL — a skill most business users, support agents, and managers don't have.

2. **Unstructured Documents** — Company policies, return rules, shipping SLAs, legal terms written in plain text files and PDFs. When a customer asks "Can I return this item after 10 days?", a human has to manually search through pages of policy documents to find the answer.

**The core problem**: Business users cannot self-serve answers from either their databases or their policy documents without depending on engineers or manually reading long documents.

### The Solution — This Project

This project builds an **AI-powered agent** that lets anyone ask questions in plain English and automatically:

- **Decides** whether the question is about **data** (e.g., revenue, orders) or **policies** (e.g., return rules, refund timelines)
- **Routes** the question to the correct AI sub-agent
- **Answers** in natural language with evidence (SQL query shown, or policy section cited)

No SQL knowledge. No document searching. Just ask and get an answer.

---

## 2. What Are We Doing In This Project?

We are building a **complete end-to-end AI pipeline** with 5 core components:

### Component 1: Data Ingestion Pipeline
- Take 9 CSV files from a real Brazilian e-commerce dataset (Olist) containing 100K+ orders
- Define the proper database schema with relationships (customers → orders → items → products → sellers)
- Load all data into a PostgreSQL database automatically

### Component 2: Text-to-SQL Agent
- The AI reads the live database schema (tables, columns, types, foreign keys)
- When a user asks a data question, GPT generates a valid SQL query
- The query is safety-checked (only SELECT allowed — no data modification)
- Results are executed against PostgreSQL and summarized in natural language

### Component 3: Document RAG (Retrieval-Augmented Generation) Engine
- The e-commerce policy document is split into small overlapping chunks
- Each chunk is converted into a numerical vector (embedding) using a local AI model
- These vectors are stored in a FAISS index for lightning-fast similarity search
- When a user asks a policy question, the most relevant chunks are retrieved and sent to GPT, which generates a grounded answer citing the specific policy section

### Component 4: Intelligent Router (The "Brain")
- A LangGraph state machine acts as the **supervisor/orchestrator**
- It uses GPT to classify every incoming question: "Is this about data or policy?"
- It routes to the correct sub-agent (SQL or RAG) automatically
- The user never has to specify which agent to use — it just works

### Component 5: Interactive CLI
- A terminal-based interface where you type questions and get answers
- The system initializes everything on startup (database, vector index, agents, router)
- Works in a continuous loop until you type "quit"

---

## 3. How Does This Target Real-World Problems?

### Real-World Use Case 1: Customer Support Teams
**Problem**: A support agent receives a customer complaint — "My order hasn't arrived. What's the policy?"
**Without this project**: The agent opens a database tool to check the order status, then searches a policy PDF for the SLA rules. Takes 5-10 minutes.
**With this project**: The agent asks two questions in plain English and gets instant answers with sources.

### Real-World Use Case 2: Business Analysts
**Problem**: A manager asks "Which product category generated the most revenue in São Paulo?"
**Without this project**: The analyst writes SQL, debugs it, runs it, and formats the results. Takes 15-30 minutes.
**With this project**: The manager types the question directly and gets the answer in seconds.

### Real-World Use Case 3: Compliance & Legal
**Problem**: "Under Brazilian consumer law, what happens if delivery is delayed by 20 days?"
**Without this project**: Someone reads through the policy document to find the relevant clause.
**With this project**: The RAG engine retrieves the exact section and GPT summarizes the answer with the section number cited.

### Real-World Use Case 4: Executive Dashboards
**Problem**: Leadership wants quick KPIs — average delivery time, payment method distribution, review scores by state.
**Without this project**: Engineering team builds custom queries and reports.
**With this project**: Anyone can ask these questions naturally and get immediate data-backed answers.

### Why This Architecture Matters
The **agentic routing pattern** (one supervisor that delegates to specialized sub-agents) is how production AI systems work at companies like:
- **Salesforce** (Einstein AI) — routes customer queries to knowledge bases or CRM data
- **Stripe** — internal tools that query transaction databases via natural language
- **Amazon** — support bots that combine order data lookup with policy retrieval

---

## 4. The Technical Blueprint — Libraries, Models & Frameworks

### Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                    USER QUERY                        │
│              "What's the return policy?"             │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│              🧭 LANGGRAPH ROUTER                     │
│         (Supervisor / Intent Classifier)             │
│                                                      │
│    GPT classifies: "sql" or "rag"                    │
└──────────┬────────────────────────────┬──────────────┘
           │                            │
     ┌─────▼─────┐              ┌───────▼───────┐
     │  SQL PATH  │              │   RAG PATH    │
     └─────┬─────┘              └───────┬───────┘
           │                            │
           ▼                            ▼
┌──────────────────┐         ┌──────────────────────┐
│ Schema Inspector │         │ Sentence-Transformer │
│  (SQLAlchemy)    │         │   Embed Question     │
└────────┬─────────┘         └──────────┬───────────┘
         │                              │
         ▼                              ▼
┌──────────────────┐         ┌──────────────────────┐
│  GPT Generates   │         │   FAISS Similarity   │
│  SQL Query       │         │   Search (Top-3)     │
└────────┬─────────┘         └──────────┬───────────┘
         │                              │
         ▼                              ▼
┌──────────────────┐         ┌──────────────────────┐
│   PostgreSQL     │         │  GPT Synthesizes     │
│   Executes SQL   │         │  Answer from Chunks  │
└────────┬─────────┘         └──────────┬───────────┘
         │                              │
         ▼                              ▼
┌──────────────────┐         ┌──────────────────────┐
│  GPT Summarizes  │         │  Grounded Answer     │
│  Results in NL   │         │  with Section Cited  │
└────────┬─────────┘         └──────────┬───────────┘
         │                              │
         └──────────────┬───────────────┘
                        ▼
              ┌──────────────────┐
              │   FINAL ANSWER   │
              │  Shown to User   │
              └──────────────────┘
```

### Complete Technology Stack

| Category | Technology | Version | What It Does In This Project |
|----------|-----------|---------|-------------------------------|
| **Language** | Python | 3.13 | The programming language everything is written in. |
| **Database** | PostgreSQL | 17.x | Stores all 9 structured e-commerce tables (orders, customers, products, etc.) on your local machine. |
| **ORM** | SQLAlchemy | 2.0+ | Defines database tables as Python classes so we never write raw CREATE TABLE SQL — it also manages connection pooling. |
| **DB Driver** | psycopg2-binary | 2.9+ | The low-level connector that lets Python talk to PostgreSQL over the network. |
| **Data Processing** | pandas | 3.0+ | Reads the CSV files into memory, cleans null values and date formats, and bulk-loads them into PostgreSQL. |
| **Vector Search** | FAISS (faiss-cpu) | 1.15+ | Facebook AI's library that stores document chunk embeddings and finds the most similar chunks to a query in milliseconds. |
| **Embeddings** | sentence-transformers | 6.0+ | Runs the `all-MiniLM-L6-v2` model locally (no API cost) to convert text into 384-dimensional numerical vectors. |
| **Embedding Model** | all-MiniLM-L6-v2 | — | A small, fast transformer model (22M parameters) that creates semantic embeddings — similar text gets similar vectors. |
| **LLM Framework** | LangChain | 1.3+ | Provides prompt templates, chains (prompt → LLM → output), and abstractions for building AI pipelines. |
| **LLM Connector** | langchain-openai | 1.6+ | Connects LangChain's chain abstraction to the OpenAI GPT API specifically. |
| **Agent Orchestrator** | LangGraph | 1.2+ | Builds a stateful graph where nodes are AI agents and edges are routing decisions — this is the "brain" of the system. |
| **LLM** | GPT-4o-mini | — | OpenAI's cost-effective language model that generates SQL queries, classifies intent, and writes natural language answers. |
| **Environment** | python-dotenv | 1.2+ | Loads the `.env` file at startup so API keys and database passwords never appear in the source code. |
| **Math** | NumPy | 2.0+ | Handles the numerical array operations needed for vector embeddings and FAISS index construction. |

### Dataset Used

| Detail | Value |
|--------|-------|
| **Name** | Brazilian E-Commerce Public Dataset by Olist |
| **Source** | Kaggle |
| **Size** | 9 CSV files, ~100K orders, ~130 MB total |
| **Time Period** | 2016–2018 |
| **Coverage** | Orders, customers, products, sellers, payments, reviews, geolocation across all Brazilian states |

### File Structure

```
Agentic Text-to-SQL & RAG Engine/
│
├── .env                          ← API keys & database URL (secrets)
├── config.py                     ← Central configuration (loads .env, sets constants)
├── main.py                       ← Entry point — run this to start the system
├── requirements.txt              ← All pip dependencies
├── PROJECT_OVERVIEW.md           ← This file — you are reading it
│
├── database/                     ← Everything related to PostgreSQL
│   ├── __init__.py               ← Package marker
│   ├── models.py                 ← 9 SQLAlchemy ORM table definitions
│   ├── connection.py             ← Engine + session factory
│   └── load_data.py              ← CSV cleaning + bulk insert script
│
├── agents/                       ← All AI agent logic
│   ├── __init__.py               ← Package marker
│   ├── rag_engine.py             ← FAISS index + policy Q&A
│   ├── sql_agent.py              ← Text-to-SQL generation + execution
│   └── router.py                 ← LangGraph supervisor/router
│
├── data/                         ← Raw data files
│   ├── ecommerce_policies.txt    ← Store policies (RAG source document)
│   └── *.csv                     ← 9 Olist e-commerce CSVs
│
└── faiss_index/                  ← Auto-generated on first run
    ├── policy.index              ← FAISS binary index
    └── chunks.json               ← Chunk text metadata
```

### How The Pieces Connect (Data Flow)

```
CSV Files ──pandas──▶ PostgreSQL ──SQLAlchemy──▶ SQL Agent ──GPT──▶ Answer
                                                     ▲
                                                     │
Policy .txt ──chunking──▶ Embeddings ──FAISS──▶ RAG Engine ──GPT──▶ Answer
                                                     ▲
                                                     │
User Question ──────────▶ LangGraph Router ──GPT──▶ Routes to correct agent
```

---

## Summary

This project is a **production-grade AI system** that combines two powerful paradigms — **Text-to-SQL** (for structured database queries) and **RAG** (for unstructured document Q&A) — under a single **agentic orchestrator** powered by LangGraph. It demonstrates how modern AI applications use specialized sub-agents coordinated by a supervisor to solve real business problems without requiring users to know SQL or manually search through documents.

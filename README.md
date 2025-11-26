📘 LLM Memory Assistant
Multi-Layer Conversational Memory Architecture (STM + Local LTM + Global LTM)
Gelişmiş, insan benzeri hafızaya sahip bir Yapay Zeka Asistanı altyapısı.
🚀 Overview
Bu proje, dil modellerine insansı hafıza yetenekleri kazandırmak için tasarlanmış çok katmanlı bir hafıza mimarisidir. Sistem:
STM (Short-Term Memory) → Oturum içindeki son mesajlar
Local LTM (Local Long-Term Memory) → Oturuma özgü kalıcı hafıza
Global LTM (Global Long-Term Memory) → Kullanıcıya özgü, oturumdan bağımsız hafıza
katmanlarını birlikte kullanarak daha tutarlı, kişiselleştirilmiş ve sürekliliği yüksek bir konuşma deneyimi sunar.
Bu proje, kendi asistanını, ürününü veya agent mimarini gerçek anlamda “hafızalı” bir yapay zekaya dönüştürmek isteyen herkes için modern ve esnek bir temel sunar.
🧠 High-Level Architecture Diagram
flowchart TD

User[User] --> UI[React UI]

UI -->|POST /api/chat| ChatAPI
UI -->|POST /api/memory/*| MemoryAPI

subgraph Backend [FastAPI Backend]
    ChatAPI[Chat Endpoint]
    MemoryAPI[Memory Endpoints]

    subgraph RetrievalEngine [Retrieval Engine]
        STM[STM Store (SQLite)]
        LTM_Local[Local LTM Store (FAISS + SQLite)]
        LTM_Global[Global LTM Store (FAISS + SQLite)]
        Reranker[MMR Reranker]
        Summarizer[Distillation / Summarizer]
    end

    MemoryPolicy[Memory Extraction Policy]
    LLM[LLM Client (Gemini/OpenAI/Any)]
end

ChatAPI --> RetrievalEngine
RetrievalEngine --> LLM
LLM --> MemoryPolicy
MemoryPolicy -->|Writeback| LTM_Local
MemoryPolicy -->|Writeback| LTM_Global
🧩 Memory Layer Structure
STM (Short-Term Memory) Diagram
sequenceDiagram
    participant U as User
    participant B as Backend
    participant STM as STM Store

    U->>B: New message
    B->>STM: Fetch last N turns
    STM-->>B: Return last N turns
    B->>U: Respond with context-aware answer
    B->>STM: Save new turn
Local LTM Retrieval Flow
flowchart LR
Query --> Embed --> FAISS_L --> Reranker --> Summarizer
FAISS_L[FAISS: Local Index]
Global LTM Retrieval Flow
flowchart LR
Query --> Embed --> FAISS_G --> Reranker --> Summarizer
FAISS_G[FAISS: Global Index]
🔍 Memory Retrieval Pipeline
sequenceDiagram
    participant U as User
    participant API as Chat API
    participant STM as STM Store
    participant LLocal as Local LTM
    participant LGlobal as Global LTM
    participant R as Reranker
    participant S as Summarizer
    participant LLM as LLM

    U->>API: user message
    API->>STM: retrieve STM turns
    API->>LLocal: similarity search
    API->>LGlobal: global similarity search

    LLocal-->>API: local results
    LGlobal-->>API: global results

    API->>R: rerank all memory
    R-->>API: ranked memories

    API->>S: distill context
    S-->>API: distilled context

    API->>LLM: final prompt with all memory layers
    LLM-->>API: response

    API->>U: reply + memory sources
📁 Project Structure
app/
 ├── api/              → Chat & Memory endpoints
 ├── core/             → Config, constants, logging
 ├── db/               → SQLite + schema.sql
 ├── services/         → STM, LTM, embeddings, retriever, policy, reranker
 ├── prompts/          → System & memory prompts
 ├── ui-frontend/      → React arayüz
 └── scripts/          → DB init, reindex
🧪 Memory Retrieval Test Scenarios (Gerçek Çıktılar)
Aşağıdaki testler sistemin hafızayı doğru yönettiğini kanıtlamak için çalıştırıldı.
Test 1 — Global LTM: Kişisel Bilgiler
Soru:
Benim adım neydi?
Cevap:
Adınız Emirhan Bey.
Soru:
Ben hangi şehirde yaşıyorum?
Cevap:
İstanbul'da yaşıyorsunuz.
Soru:
Sabahları ne içiyordum?
Cevap:
Sabahları genellikle latte içiyordunuz.
💡 Bu bilgiler oturumdan bağımsız olarak Global LTM’den geri çağrıldı.
Test 2 — Local LTM: Oturuma Özgü Kararlar
Soru:
Bu session’da neyi kararlaştırmıştık?
Cevap:
"SmartCart AI" ürün öneri modülü için TF-IDF + embedding hibrit arama kullanacağımızı kararlaştırdık.
💡 Bu bilgi sadece ilgili oturuma special olduğu için Local LTM’den geldi.
Test 3 — Proje Hatırlama (Global LTM)
Soru:
Benim üzerinde çalıştığım proje neydi?
Cevap:
SmartCart AI projesi üzerinde çalışıyorsunuz.
💡 Sistem, önce STM’ye baktı; bulamadı → sonra Local LTM kontrol etti → yoksa Global LTM’den getirdi.
Test 4 — Görev Hatırlatma
Soru:
Bu sohbet içinde sana küçük bir görev vereyim: Bana bu sohbetin sonunda market chatbot fikrini hatırlat.
Devamında:
Şu an bu görev neydi?
Cevap:
Bu sohbetin sonunda size market chatbot fikrini hatırlatmam gerekiyor.
💡 Görev Local LTM’ye doğru şekilde yazıldı ve oradan geri çağrıldı.
Test 5 — Hafıza Layer Dengesi
Aynı anda:
STM → Güncel konuşma
Local LTM → Oturumdaki kararlar
Global LTM → Üst seviye profil bilgileri
tamamen doğru bağlantılarla geri çağrıldı.
➡ Sonuç: Sistem eksiksiz çalışıyor.
⚙️ Installation & Run
1. Backend
pip install -r requirements.txt
uvicorn app.main:app --reload
2. Database Initialization
python app/scripts/init_db.py
3. Frontend
cd app/ui-frontend
npm install
npm run dev
📡 API Endpoints
Chat
POST /api/chat
Local Memory
POST /api/memory/local
Global Memory
POST /api/memory/global
Memory Search
POST /api/memory/search
🏁 Conclusion
Bu proje, büyük dil modellerine gerçek anlamda kişisel hafıza kazandırmak için modern, modüler ve esnek bir çözüm sunar.
Çok katmanlı hafıza mimarisi
STM + Local LTM + Global LTM
Embedding + FAISS + Reranker + Summarizer pipeline
Tam entegre React UI
Test edilmiş, gerçek senaryolarla doğrulanmış hafıza davranışı
Gelecekte:
Multi-user desteği
Voice agent entegrasyonu
Memory pruning / scoring
Graph-based memory
gibi modüller kolayca eklenebilir.

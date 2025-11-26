# LLM Memory Assistant  
**STM + Local LTM + Global LTM ile Çok Katmanlı Hafıza Mimarisi**

Bu proje, bir yapay zekâ asistanına **gerçek bir hafıza sistemi** kazandırmak için tasarlanmış çok katmanlı bir mimari sunar.  
Sistem; kısa vadeli bağlam yönetimi, oturum bazlı uzun vadeli hafıza ve kullanıcı çapında global hafıza katmanlarını bir araya getirerek **kalıcı, tutarlı ve kişiselleştirilmiş** bir etkileşim sağlar.

---

## 🚀 Özellikler

### 🧠 **1. STM — Short-Term Memory (Kısa Vadeli Hafıza)**
- Sadece mevcut oturumda (session) son N mesajı tutar.
- Bağlam kopmadan konuşma akışının sürmesini sağlar.
- Oturum kapandığında temizlenir.

### 🗂️ **2. Local LTM — Session-Scoped Long-Term Memory**
- Her oturumda konuşulan **kalıcı ve değerli** bilgileri saklar.
- Farklı konular için farklı oturum hafızaları oluşturur.
- Aynı oturum tekrar açıldığında konuşma detayları geri çağrılır.

### 🌍 **3. Global LTM — User-Scoped Long-Term Memory**
- Kullanıcıya ait gerçekler, tercihler, proje bilgileri vb. uzun vadeli hafızayı tutar.
- Tüm oturumlar arasında ortak bilgi kaynağıdır.

### 🔍 **Akıllı Hafıza Retrieval**
- STM → Local LTM → Global LTM öncelik sırası
- Embedding tabanlı semantic search
- Similarity threshold
- MMR reranking
- Hafıza distillation (özetleme)

### ✨ **LLM-Destekli Memory Extraction**
- Her mesaj sonrası LLM tarafından memory extraction yapılır.
- memory_policy kurallarına göre 0–5 memory çıkarılır.
- Doğru veriler Local & Global LTM'e otomatik yazılır.

### 🧩 **Frontend**
- React + TypeScript UI  
- Oturum listesi  
- Mesajlaşma ekranı  
- Memory kaynak gösterimi  

---

# 📁 Proje Mimarı ve Dizini

```plaintext
app/
├── api/                 # API endpointleri
├── core/                # Config, logging, constants
├── db/                  # SQLite repository & schema
├── services/            # STM, LTM, Retriever, Memory Policy, LLM Client
├── prompts/             # System & retrieval prompt dosyaları
├── ui-frontend/         # React + TypeScript UI
└── scripts/             # DB init & index rebuild scriptleri

```
🧩 Mimari Diyagramlar
1️⃣ Genel Hafıza Mimarisi

flowchart TD
    UserMessage[User Message] --> Retriever

    Retriever --> STM[(STM)]
    Retriever --> LocalLTM[(Local LTM)]
    Retriever --> GlobalLTM[(Global LTM)]

    STM --> ContextMerge
    LocalLTM --> ContextMerge
    GlobalLTM --> ContextMerge

    ContextMerge --> LLM[LLM Generate Reply]
    LLM --> Reply[Assistant Reply]

    Reply --> MemoryPolicy
    MemoryPolicy --> LocalLTM
    MemoryPolicy --> GlobalLTM

2️⃣ Memory Writeback Akışı

sequenceDiagram
    participant U as User
    participant A as Assistant
    participant MP as Memory Policy
    participant L as Local LTM
    participant G as Global LTM

    U->>A: Mesaj gönderir
    A->>MP: Message + Reply → Memory analiz isteği
    MP->>MP: Extraction (0–5 memory)
    alt Local memories
        MP->>L: write_local_memory()
    end
    alt Global memories
        MP->>G: write_global_memory()
    end

3️⃣ Retriever Veri Akışı

flowchart LR
    Query[User Query] --> STMQuery[STM Search]
    Query --> LocalQuery[Local LTM Search]
    Query --> GlobalQuery[Global LTM Search]

    STMQuery --> Merge
    LocalQuery --> Merge
    GlobalQuery --> Merge

    Merge --> Rerank[MMR Rerank]
    Rerank --> Distill[Distilled Context]
    Distill --> FinalPrompt[Final Prompt to LLM]

```
🔬 Örnek Hafıza Senaryosu

Aşağıdaki örnek STM, Local LTM ve Global LTM katmanlarının nasıl birlikte çalıştığını göstermektedir.

```
🎯 Global Memory — Proje Bilgisi

User:
Aslında bir süredir şunu planlıyorum: Market alışverişi için kişisel öneriler sunan
bir akıllı asistan geliştirmek istiyorum. İsmi de "SmartCart AI" olsun.
Bu uzun vadeli bir proje fikridir.

Assistant → Global LTM’e kaydedilir.

Artık şu soruya her oturumda yanıt verebilir:

Benim üzerinde çalıştığım proje neydi?

Cevap:

SmartCart AI projesi üzerinde çalışıyorsunuz.

```
📁 Local Memory — Oturum Bazlı Hatırlama

User:

Bu session’da neyi kararlaştırmıştık?

Assistant (Local LTM’den çağırır):

SmartCart AI ürün öneri modülü için TF-IDF + embedding hibrit arama
kullanacağımızı kararlaştırmıştık.

```
🔁 STM — Yakın Bağlam Hatırlama

Aynı oturum içindeki son mesajlar STM ile tutulur.

🧪 Gerçek Test Çıktıları (Kullanıcı Testlerinden)
✔️ Global Memory — Kişisel Bilgiler

User:

Benim adım neydi?


Assistant:

Adınız Emirhan Bey.


User:

Ben hangi şehirde yaşıyorum?


Assistant:

İstanbul'da yaşıyorsunuz.


User:

Sabahları ne içiyordum?


Assistant:

Sabahları genellikle latte içiyordunuz.

```
✔️ Global Memory — Proje Bilgisi

User:

Benim üzerinde çalıştığım proje neydi?


Assistant:

SmartCart AI adında bir proje üzerinde çalışıyorsunuz.

```
✔️ Local Memory — Session-Specific Kararlar

User:

Bu session’da neyi kararlaştırmıştık?


Assistant:

SmartCart AI ürün öneri modülü için TF-IDF + embedding hibrit yaklaşımını
kullanacağımızı kesinleştirdik.
```
```
🛠 Kurulum
🔧 Backend (FastAPI)
pip install -r requirements.txt
uvicorn app.main:app --reload
```
🎨 Frontend (React + TypeScript)

```
cd app/ui-frontend
npm install
npm run dev
```
📌 Çevresel Değişkenler (.env)

```
APP_ENV=development
API_KEY=buraya_api_key
EMBED_MODEL=fallback
LLM_MODEL=fallback
```
📝 Lisans

```
MIT License
```
⭐ Katkı
Pull request gönderebilir, issue açabilir, geliştirmeye katkıda bulunabilirsiniz.

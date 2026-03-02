MarketPulse'un scraping pipeline'ı zaten bir ajan trajectory'si:

  # Mevcut MarketPulse scraping akışı (scraping.py):

  Turn 0: action=navigate("hepsiburada.com/search?q=kulaklık")
          observation={"page_loaded": true, "products": 48}

  Turn 1: action=parse_search_results()
          observation={"organic": 24, "sponsored": 12, "brands": [...]}

  Turn 2: action=click_product("kulaklık-x200")
          observation={"price": 599, "seller": "TechShop",
                       "rating": 4.2, "stock": "in_stock"}

  Turn 3: action=get_other_sellers("kulaklık-x200")
          observation={"sellers": [
            {"name": "TechShop", "price": 599},
            {"name": "SesShop", "price": 549},
            {"name": "ElektroMarket", "price": 619}
          ]}

  Turn 4: action=get_reviews("kulaklık-x200", last=50)
          observation={"avg_rating": 4.2, "count": 1847,
                       "recent_complaints": ["ses kalitesi", "kablo"]}

  Turn 5: action=save_snapshot(product_id, price=599, rating=4.2)
          observation={"snapshot_id": 4521, "saved": true}

  Ve price_monitor_service.py'deki monitoring akışı:
  # Günlük fiyat takibi
  Turn 0: fetch_all_monitored_products()     → 340 ürün
  Turn 1: batch_scrape(batch_1, 40 ürün)     → 38 başarılı, 2 timeout
  Turn 2: batch_scrape(batch_2, 40 ürün)     → 40 başarılı
  ...
  Turn 8: compare_with_previous_snapshots()  → 12 fiyat değişimi
  Turn 9: detect_anomalies()                 → 2 anormal düşüş (%40+)
  Turn 10: generate_alerts()                 → 2 alert oluşturuldu

  AMA-Agent Bu Pipeline'a Ne Katar?

  3 somut değer:

  Değer 1: Scraping Hata Hafızası (Causality Graph)

  Sorun: Hepsiburada bot detection'a takılıyor, her seferinde
  farklı workaround deneniyor ama hangi çözümün işe yaradığı unutuluyor.

  AMA-Agent ile:

  Causality Graph kaydeder:
    [ScraperAPI kullan]──causes──→[403 hatası]
         @session_45                   │
                                    causes
                                       ▼
    [Bright Data'ya geç]──causes──→[Başarılı ama yavaş]
                                       │
                                    causes
                                       ▼
    [playwright-stealth ekle]──causes──→[Başarılı + hızlı ✓]

  Sonraki 403 hatasında sistem sorar ve cevap alır:
    "Bu site için en son playwright-stealth + Bright Data
     kombinasyonu işe yaramıştı (session_45, turn 3-7)"

  Değer 2: Fiyat Anomali Nedensellik Zinciri

  Sorun: Bir ürünün fiyatı %40 düştü. Gerçek indirim mi,
  hatalı scraping mi, satıcı değişikliği mi?

  AMA-Agent Causality Graph:

    [snapshot@t1: price=599, seller=TechShop]
         │
      causes (seller_change)
         ▼
    [snapshot@t2: price=359, seller=YENI_SATICI]
         │
      associated
         ▼
    [other_sellers@t2: TechShop hala 599'da]

  Çıkarım: "Fiyat düşüşü gerçek indirim değil,
    default satıcı değişti. TechShop hala 599."

  Değer 3: Kategori Keşif Stratejisi Hafızası

  Sorun: category_scraper hangi kategorilerde hangi
  stratejiyle daha iyi sonuç alıyor, bilinmiyor.

  AMA-Agent trajectory kaydı:
    [kategori: elektronik, strateji: pagination]──causes──→[500 ürün, 3dk]
    [kategori: moda, strateji: pagination]──causes──→[timeout, 0 ürün]
    [kategori: moda, strateji: infinite_scroll]──causes──→[800 ürün, 5dk]

  Sonraki "moda" kategori taramasında:
    "Bu kategori için infinite_scroll stratejisi kullan,
     pagination geçen 3 denemede de timeout verdi."

  ---
  Somut Entegrasyon Mimarisi

  ┌─────────────────────────────────────────────────────────┐
  │  MarketPulse Mevcut Mimari                               │
  │                                                          │
  │  Frontend (React) ←──→ FastAPI ←──→ PostgreSQL           │
  │                           │            │                  │
  │                        Celery ←──→ Redis                  │
  │                           │                               │
  │                    ┌──────┴──────┐                        │
  │                    │  Services   │                        │
  │                    ├─────────────┤                        │
  │                    │ scraping.py │                        │
  │                    │ price_mon.  │                        │
  │                    │ llm_service │                        │
  │                    │ category_s. │                        │
  │                    └──────┬──────┘                        │
  │                           │                               │
  │                    ┌──────▼──────────────────────────┐   │
  │                    │  YENİ: AMA Memory Layer         │   │
  │                    │                                  │   │
  │                    │  ┌─────────────────────────────┐│   │
  │                    │  │ Trajectory Logger            ││   │
  │                    │  │ Her servis çağrısını kaydet  ││   │
  │                    │  └────────────┬────────────────┘│   │
  │                    │               │                  │   │
  │                    │  ┌────────────▼────────────────┐│   │
  │                    │  │ Causality Graph Builder      ││   │
  │                    │  │ State değişimlerini izle     ││   │
  │                    │  │ Nedensellik kenarları kur    ││   │
  │                    │  └────────────┬────────────────┘│   │
  │                    │               │                  │   │
  │                    │  ┌────────────▼────────────────┐│   │
  │                    │  │ Memory Retriever             ││   │
  │                    │  │ Geçmiş deneyimleri sorgula  ││   │
  │                    │  └─────────────────────────────┘│   │
  │                    └─────────────────────────────────┘   │
  └─────────────────────────────────────────────────────────┘

  Dosya Yapısı (MarketPulse'a eklenecek)

  backend/app/services/
  ├── scraping.py               # Mevcut
  ├── llm_service.py            # Mevcut
  ├── price_monitor_service.py  # Mevcut
  │
  ├── ama_memory/               # YENİ — AMA-Agent katmanı
  │   ├── __init__.py
  │   ├── config.py             # API anahtarları, model seçimi
  │   ├── trajectory_logger.py  # Action-observation kaydı
  │   ├── graph_builder.py      # Causality Graph inşası
  │   ├── retriever.py          # Hafıza sorgusu
  │   ├── state_extractor.py    # LLM ile durum çıkarımı
  │   └── models.py             # SQLAlchemy modelleri (graph storage)

  backend/app/db/models.py      # Ek tablolar:
    # ama_trajectories     — Ham trajectory kayıtları
    # ama_graph_nodes      — Causality Graph düğümleri
    # ama_graph_edges      — Graf kenarları
    # ama_embeddings       — Düğüm vektörleri

  Kod Entegrasyonu — Somut Örnek

  trajectory_logger.py:
  from datetime import datetime
  from app.db.database import get_db
  from app.db.models import AMATrajectory

  class TrajectoryLogger:
      def __init__(self, session_id: str, task_description: str):
          self.session_id = session_id
          self.task = task_description
          self.turn_idx = 0

      def log_turn(self, action: str, action_params: dict,
                   observation: dict, db):
          """Her scraping adımını kaydet."""
          turn = AMATrajectory(
              session_id=self.session_id,
              turn_idx=self.turn_idx,
              action=action,
              action_params=action_params,  # JSON
              observation=observation,       # JSON
              timestamp=datetime.utcnow()
          )
          db.add(turn)
          db.commit()
          self.turn_idx += 1
          return turn

  scraping.py'ye entegrasyon (mevcut koda minimal ekleme):
  # backend/app/services/scraping.py — mevcut fonksiyon

  async def scrape_search_results(keyword, platform, proxy_provider, db):
      # YENİ: Trajectory logger başlat
      logger = TrajectoryLogger(
          session_id=f"search_{keyword}_{datetime.now().isoformat()}",
          task_description=f"Search '{keyword}' on {platform}"
      )

      # Mevcut kod — hiçbir şey değişmiyor
      page = await browser.new_page()

      url = build_search_url(keyword, platform)
      response = await page.goto(url)

      # YENİ: Turn kaydet
      logger.log_turn(
          action="navigate",
          action_params={"url": url, "platform": platform},
          observation={"status": response.status, "url": page.url},
          db=db
      )

      # Mevcut parse kodu
      products = await parse_search_page(page)

      # YENİ: Turn kaydet
      logger.log_turn(
          action="parse_search_results",
          action_params={"keyword": keyword},
          observation={
              "total_products": len(products),
              "sponsored_count": sum(1 for p in products if p.is_sponsored),
              "organic_count": sum(1 for p in products if not p.is_sponsored)
          },
          db=db
      )

      # ... devam eden mevcut kod aynı kalır

  state_extractor.py — LLM ile durum çıkarımı (API-based):
  from openai import OpenAI  # Zaten MarketPulse'ta var

  # MarketPulse'un mevcut OPENAI_API_KEY'ini kullan
  client = OpenAI()

  async def extract_state_from_turns(prev_turn: dict, curr_turn: dict,
                                       task: str) -> dict:
      """AMA-Agent'ın A1 aşaması — turn çiftinden durum çıkar."""

      prompt = f"""
      Bir e-ticaret scraping ajanının trajectory'sini analiz ediyorsun.
   
      Görev: {task}
      Önceki turn: {json.dumps(prev_turn, ensure_ascii=False)}
      Mevcut turn: {json.dumps(curr_turn, ensure_ascii=False)}
   
      JSON formatında döndür:
      {{
        "env_state": {{"key": "value"}},
        "objectives": [{{"name": "...", "status": "..."}}],
        "state_changed": true/false,
        "causality": "önceki aksiyonun bu sonuca nasıl yol açtığı"
      }}
      """

      response = client.chat.completions.create(
          model="gpt-4o-mini",  # Zaten MarketPulse'ta kullanılan model
          messages=[{"role": "user", "content": prompt}],
          temperature=0.3,       # Düşük — tutarlı çıkarım
          max_tokens=500,
          response_format={"type": "json_object"}
      )

      return json.loads(response.choices[0].message.content)

  retriever.py — Hafıza sorgusu:
  from sentence_transformers import SentenceTransformer

  model = SentenceTransformer('all-MiniLM-L6-v2')  # 80MB, CPU'da hızlı

  class AMARetriever:
      def __init__(self, db):
          self.db = db

      async def query(self, question: str, project: str = "marketpulse"):
          """AMA-Agent'ın B1→B4 pipeline'ı."""

          # B1: Top-K embedding similarity
          q_emb = model.encode(question)
          similar_nodes = self._find_similar_nodes(q_emb, top_k=5)

          # B2: Self-evaluation — yeterli mi?
          eval_result = await self._evaluate_sufficiency(
              question, similar_nodes
          )

          if eval_result["decision"] == "SUFFICIENT":
              return eval_result["answer"]

          elif eval_result["decision"] == "NEED_GRAPH":
              # B3: Graf traversal
              expanded = self._traverse_graph(
                  node_ids=eval_result["target_nodes"],
                  depth=eval_result.get("depth", 2)
              )
              return await self._synthesize_answer(question, expanded)

          elif eval_result["decision"] == "NEED_CODE":
              # B3': Bu kısım MarketPulse'ta gereksiz
              # SQL query ile veri çekmek yeterli
              return await self._sql_search(question)

      async def _evaluate_sufficiency(self, question, nodes):
          """AMA-Agent'ın B2 aşaması."""
          response = client.chat.completions.create(
              model="gpt-4o-mini",
              messages=[{
                  "role": "user",
                  "content": f"""
                  Soru: {question}
                  Bulunan hafıza düğümleri: {json.dumps(nodes)}
   
                  Bu bilgiler soruyu cevaplamaya yeterli mi?
                  SUFFICIENT / NEED_GRAPH / NEED_MORE şeklinde cevapla.
                  SUFFICIENT ise cevabı da ver.
                  """
              }],
              temperature=0.2
          )
          return parse_evaluation(response)

  Veritabanı Modelleri (mevcut models.py'ye ekle)

  # backend/app/db/models.py — mevcut dosyaya ekle

  class AMATrajectory(Base):
      __tablename__ = "ama_trajectories"

      id = Column(Integer, primary_key=True)
      session_id = Column(String, index=True)
      turn_idx = Column(Integer)
      action = Column(String)           # "navigate", "parse", "save"
      action_params = Column(JSON)
      observation = Column(JSON)
      timestamp = Column(DateTime)

  class AMAGraphNode(Base):
      __tablename__ = "ama_graph_nodes"

      id = Column(Integer, primary_key=True)
      session_id = Column(String, index=True)
      turn_idx = Column(Integer)
      node_type = Column(String)        # "env_state", "objective_state"
      state_data = Column(JSON)
      embedding = Column(LargeBinary)   # numpy array as bytes
      created_at = Column(DateTime)

  class AMAGraphEdge(Base):
      __tablename__ = "ama_graph_edges"

      id = Column(Integer, primary_key=True)
      source_node_id = Column(Integer, ForeignKey("ama_graph_nodes.id"))
      target_node_id = Column(Integer, ForeignKey("ama_graph_nodes.id"))
      edge_type = Column(String)        # "causality", "association", "similarity"
      metadata = Column(JSON)

  Alembic migration:
  cd backend
  alembic revision --autogenerate -m "add AMA memory tables"
  alembic upgrade head

  ---
  API Endpoint (mevcut FastAPI'ye ekle)

  # backend/app/api/memory_routes.py — YENİ

  from fastapi import APIRouter, Depends
  from app.services.ama_memory.retriever import AMARetriever

  router = APIRouter(prefix="/api/memory", tags=["AMA Memory"])

  @router.get("/query")
  async def query_memory(q: str, db=Depends(get_db)):
      """Geçmiş scraping deneyimlerini sorgula."""
      retriever = AMARetriever(db)
      result = await retriever.query(q)
      return {"answer": result}

  @router.get("/graph/{session_id}")
  async def get_session_graph(session_id: str, db=Depends(get_db)):
      """Bir scraping oturumunun causality graph'ını getir."""
      nodes = db.query(AMAGraphNode).filter_by(session_id=session_id).all()
      edges = db.query(AMAGraphEdge).filter(
          AMAGraphEdge.source_node_id.in_([n.id for n in nodes])
      ).all()
      return {"nodes": nodes, "edges": edges}

  @router.get("/stats")
  async def memory_stats(db=Depends(get_db)):
      """Hafıza istatistikleri."""
      return {
          "total_sessions": db.query(AMATrajectory.session_id).distinct().count(),
          "total_turns": db.query(AMATrajectory).count(),
          "total_nodes": db.query(AMAGraphNode).count(),
          "total_edges": db.query(AMAGraphEdge).count(),
      }

  ---
  Maliyet Hesabı (MarketPulse Senaryosu)

  Günlük MarketPulse operasyonu:
  ├── 340 ürün fiyat takibi → ~340 turn
  ├── 5 arama görevi → ~50 turn
  ├── 2 kategori taraması → ~200 turn
  └── Toplam: ~590 turn/gün

  AMA-Agent maliyeti (gpt-4o-mini fiyatlarıyla):
  ├── A1 Durum çıkarımı: 590 turn × ~800 token = ~472K token
  │   └── Girdi: ~354K ($0.053) + Çıktı: ~118K ($0.047) = ~$0.10/gün
  │
  ├── A3 Embedding: 590 × all-MiniLM-L6-v2
  │   └── Lokal model, $0.00
  │
  ├── B2 Self-eval (sorgulama başına): ~2K token
  │   └── Günde ~10 sorgu = ~$0.003
  │
  └── TOPLAM: ~$0.10/gün = ~$3/ay

  Karşılaştırma:
  ├── Mevcut LLM maliyeti (llm_service.py): ~$5-15/ay
  ├── AMA hafıza ekleme: +$3/ay
  └── Artış: %20-60 — makul

  ---
  Hangi Model API'si Kullanmalı?

  ┌───────────────┬─────────────────────┬────────────────┬──────────────────────┬─────────────────────────────────────┐
  │     Model     │ Durum Çıkarımı (A1) │ Self-eval (B2) │       Maliyet        │                Öneri                │
  ├───────────────┼─────────────────────┼────────────────┼──────────────────────┼─────────────────────────────────────┤
  │ gpt-4o-mini   │ İyi                 │ İyi            │ Düşük ($0.15/1M)     │ Zaten MarketPulse'ta var, en pratik │
  ├───────────────┼─────────────────────┼────────────────┼──────────────────────┼─────────────────────────────────────┤
  │ Claude Haiku  │ İyi                 │ İyi            │ Düşük ($0.25/1M)     │ Alternatif                          │
  ├───────────────┼─────────────────────┼────────────────┼──────────────────────┼─────────────────────────────────────┤
  │ DeepSeek-V3   │ İyi                 │ Orta           │ Çok düşük ($0.07/1M) │ Bütçe dostu                         │
  ├───────────────┼─────────────────────┼────────────────┼──────────────────────┼─────────────────────────────────────┤
  │ gpt-4o        │ Çok iyi             │ Çok iyi        │ Orta ($2.50/1M)      │ Sadece kritik sorgular için         │
  ├───────────────┼─────────────────────┼────────────────┼──────────────────────┼─────────────────────────────────────┤
  │ Claude Sonnet │ Çok iyi             │ Çok iyi        │ Orta ($3/1M)         │ Kalite gerekiyorsa                  │
  └───────────────┴─────────────────────┴────────────────┴──────────────────────┴─────────────────────────────────────┘

  Önerim: gpt-4o-mini. Zaten MarketPulse'ta kullanılıyor, ek API key gerektirmez, maliyet düşük, durum çıkarımı için yeterli.

  Embedding: all-MiniLM-L6-v2. Lokal çalışır, API gerektirmez, 80MB, CPU'da hızlı. MarketPulse backend'ine sentence-transformers pip eklemek yeterli.

  ---
  Sonuç

  ┌─────────────────────────────────────┬───────────────────────────────────────────────────────────────────────────┐
  │                Soru                 │                                   Cevap                                   │
  ├─────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────┤
  │ Ürünün içine entegre edilebilir mi? │ Evet — scraping ve monitoring pipeline'larına trajectory logger ekleyerek │
  ├─────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────┤
  │ Geliştirmede kullanılabilir mi?     │ Evet ama overkill — A-MEM Zettelkasten planımız daha uygun                │
  ├─────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────┤
  │ API ile çalışır mı?                 │ Evet — gpt-4o-mini + lokal embedding modeli yeterli                       │
  ├─────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────┤
  │ Ne kadar efor?                      │ ~3-5 dosya ekleme, mevcut koda minimal değişiklik                         │
  ├─────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────┤
  │ Maliyet?                            │ ~$3/ay ek (gpt-4o-mini fiyatlarıyla)                                      │
  ├─────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────┤
  │ En büyük değer nerede?              │ Scraping hata hafızası + fiyat anomali nedensellik zinciri                │
  └─────────────────────────────────────┴───────────────────────────────────────────────────────────────────────────┘

  En pratik başlangıç: trajectory_logger.py'yi yaz, scraping.py'ye 5-6 satır log çağrısı ekle, birkaç hafta veri biriktir, sonra Causality Graph ve retrieval katmanını inşa et.



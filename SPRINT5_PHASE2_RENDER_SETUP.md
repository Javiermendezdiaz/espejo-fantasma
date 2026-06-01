# SPRINT 5 PHASE 2-5 — RENDER.COM DEPLOYMENT SETUP

**PRECONDICIÓN:** Git repo `diagnostico-fantasma` creado en GitHub con todos 18 archivos en `main` branch.

---

## PHASE 2 — Create Render Web Service + PostgreSQL

### Step 1: Create PostgreSQL Database

1. Ve a https://dashboard.render.com/
2. Haz login (o crea cuenta)
3. **New +** → **PostgreSQL** → **New PostgreSQL**
4. Configurar:
   - **Name:** `espejo-fantasma-db`
   - **Database:** `espejo_fantasma_prod` (será `espejo_fantasma_prod`)
   - **User:** `javier` (default, puede cambiar)
   - **Version:** 16 (seleccionar en dropdown)
   - **Region:** Frankfurt (eu-central-1) — más cercano a España
   - **Data Center:** Frankfurt
   - **Tier:** Free (o Starter si necesitas garantías)
5. Crear database
6. **Copiar connection string** (formato: `postgresql://[user]:[password]@[host]:[port]/[database]`)
   - Guardar en texto plano seguro (lo necesitarás en el Web Service)

**Esperar ~2 minutos** hasta que esté ready (status "Available").

---

### Step 2: Create Web Service

1. Render Dashboard → **New +** → **Web Service**
2. **Connect repository:**
   - Selecciona "GitHub" (autoriza si es primera vez)
   - Busca y selecciona repositorio `diagnostico-fantasma`
   - Branch: `main`
3. **Configuración del servicio:**
   - **Name:** `espejo-fantasma-api`
   - **Runtime:** Python 3
   - **Build command:** 
     ```
     pip install -r requirements.txt && python migrate.py
     ```
   - **Start command:** 
     ```
     uvicorn app_couple_endpoints:app --host 0.0.0.0 --port $PORT
     ```
   - **Region:** Frankfurt (mismo que DB)
   - **Instance Type:** Free (o Starter)
   - **Auto-deploy:** ON (redeploy en cada push a main)

---

## PHASE 3 — Configure Environment Variables

En Render Web Service → **Environment**:

```
DATABASE_URL=postgresql://javier:[PASSWORD]@[HOST]:[PORT]/espejo_fantasma_prod
STRIPE_API_KEY=sk_test_... (o sk_live_ cuando go live)
STRIPE_WEBHOOK_SECRET=whsec_... (después de webhook setup)
API_HOST=0.0.0.0
API_PORT=8000
API_BASE_URL=https://espejo-fantasma-api.onrender.com
FRONTEND_URL=https://[FRONTEND_DOMAIN]
SECRET_KEY=generate_random_32_char_string
PBKDF2_ITERATIONS=480000
GDPR_RETENTION_DAYS=72
DATA_DELETION_ENABLED=true
ENVIRONMENT=production
LOG_LEVEL=info
```

**Generar SECRET_KEY (local terminal):**
```python
import secrets
print(secrets.token_urlsafe(32))
```

---

## PHASE 4 — Database Migration + Health Check

### Verificar migration automática:

1. Render → Servicio → **Logs** → buscar:
   ```
   INFO:     Application startup complete
   ```
2. Abrir endpoint health check:
   ```
   curl https://espejo-fantasma-api.onrender.com/ping
   ```
   Debe retornar:
   ```json
   {
     "status": "ok",
     "timestamp": "2026-06-01T..."
   }
   ```

Si falla migration, ejecutar manualmente:
```bash
# En Render shell (no terminal local)
python migrate.py
```

---

## PHASE 5 — Test 5 Endpoints (sin frontend, curl/Postman)

### Endpoint 1: Health Check
```bash
curl -X GET https://espejo-fantasma-api.onrender.com/ping
```

### Endpoint 2: Init Blind Session
```bash
curl -X POST https://espejo-fantasma-api.onrender.com/blind-session/init \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "couple_id=test-couple-001&client_ip=127.0.0.1&client_ua=Mozilla/5.0"
```

Guarda los tokens retornados: `token_a` y `token_b`.

### Endpoint 3: Submit Answers (con mock data)

Crea archivo `test_answers.json`:
```json
{
  "couple_id": "test-couple-001",
  "user_a_answers": {"1": 5, "2": 4, "3": 3, "4": 2, "5": 1},
  "user_b_answers": {"1": 4, "2": 5, "3": 2, "4": 3, "5": 1},
  "token_a": "[TOKEN_A_FROM_STEP_2]",
  "token_b": "[TOKEN_B_FROM_STEP_2]"
}
```

```bash
curl -X POST https://espejo-fantasma-api.onrender.com/couple/test-couple-001/answers \
  -H "Content-Type: application/json" \
  -d @test_answers.json
```

Retorna análisis + `pdf_url`.

### Endpoint 4: Get Result
```bash
curl -X GET https://espejo-fantasma-api.onrender.com/couple/test-couple-001/result
```

### Endpoint 5: Get Metrics
```bash
curl -X GET https://espejo-fantasma-api.onrender.com/metrics
```

**Si todo retorna 200 OK y datos coherentes: ✅ ENDPOINTS WORKING**

---

## ✅ FASES 2-5 COMPLETE

Próximo: **SPRINT 5 PHASE 6 — Configure Stripe Webhooks (live mode)**

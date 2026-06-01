# SPRINT 5 — LIVE DEPLOYMENT EXECUTION GUIDE
**Status:** BLOCKING TASK — Ejecutar AHORA para desbloquear SPRINT 8 en producción  
**Timestamp:** 2026-06-01  
**Role:** Javier (usuario) — ACCIÓN REQUERIDA

---

## 🎯 Objetivo

Desplegar el sistema **Diagnóstico Financiero de Parejas + Stripe SUPREMO** a producción en Render.com con PostgreSQL, webhooks y todas las variables de entorno correctamente configuradas.

---

## ⚠️ BLOCKER: Tu acción es REQUERIDA

**NO puedo hacer esto por ti** — GitHub no me permite hacer push desde el sandbox. Tienes que ejecutar 3 comandos en tu terminal PowerShell local.

---

## 📋 CHECKLIST PASO-A-PASO

### FASE 1: Git Initialization (TU TERMINAL LOCAL)

**Abrir PowerShell en:**  
`C:\Users\javie\OneDrive\Escritorio\diagnostico financiero\`

**Ejecutar estos comandos EN ORDEN:**

```powershell
# 1. Initialize git (PRIMERA VEZ SOLO)
git init

# 2. Add remote (PRIMERA VEZ SOLO)
git remote add origin https://github.com/TU_USERNAME/diagnostico-financiero.git

# 3. Add all files
git add .

# 4. Commit
git commit -m "SPRINT 8 SUPREMO: Stripe integration + 6 IxD mechanics + Psychological pricing"

# 5. Push to main branch (PRIMERA VEZ: usa --set-upstream)
git push -u origin main

# Si ya existe remoto: git push origin main
```

**Verificar en GitHub:** https://github.com/TU_USERNAME/diagnostico-financiero

---

### FASE 2: Render.com Setup (TU PANEL WEB)

**Ir a:** https://dashboard.render.com

#### 2A: Create PostgreSQL Database

1. Click **"New +"** → **"PostgreSQL"**
2. **Name:** `diagnostico-db`
3. **Database:** `diagnostico_prod`
4. **User:** `postgres`
5. **Region:** Frankfurt (EU, cercano a Madrid)
6. **Click Create**
7. **Esperar 2-3 minutos** hasta que esté "Available"
8. **Copiar estos datos:**
   ```
   External Database URL: postgresql://...
   Username: postgres
   Password: [Render genera una aleatoria — GUARDAR]
   Database: diagnostico_prod
   Host: [render.com address]
   Port: 5432
   ```

#### 2B: Create Web Service

1. Click **"New +"** → **"Web Service"**
2. **Repository:** Conectar tu GitHub repo `diagnostico-financiero`
3. **Name:** `espejo-fantasma-api` (o como prefieras)
4. **Environment:** Python 3
5. **Build Command:** `pip install -r requirements.txt`
6. **Start Command:** `uvicorn app_couple_endpoints:app --host 0.0.0.0 --port $PORT`
7. **Plan:** Free (o Starter si quieres persistencia mejor)
8. **Environment Variables:** (ver FASE 3)

---

### FASE 3: Environment Variables (RENDER PANEL)

**En la sección "Environment" del Web Service, agregar:**

```
DATABASE_URL=postgresql://postgres:PASSWORD@HOST:5432/diagnostico_prod
STRIPE_API_KEY=sk_test_XXXXX  [obtener de Stripe Dashboard → API Keys]
STRIPE_PUBLISHABLE_KEY=pk_test_XXXXX
STRIPE_WEBHOOK_SECRET=whsec_XXXXX  [crear webhook en Stripe]
JWT_SECRET=TU_SECRET_ALEATORIO_LARGO
LOG_LEVEL=info
```

**Para obtener Stripe keys:**
1. Ir a https://dashboard.stripe.com/apikeys
2. Copiar "Secret key" → `STRIPE_API_KEY`
3. Copiar "Publishable key" → `STRIPE_PUBLISHABLE_KEY`

**Para crear Webhook Secret:**
1. Ir a https://dashboard.stripe.com/webhooks
2. Click "Add an endpoint"
3. URL: `https://TU_RENDER_URL/webhooks/stripe`
4. Events to send: `payment_intent.succeeded`, `payment_intent.payment_failed`, `charge.refunded`
5. Copiar "Signing secret" → `STRIPE_WEBHOOK_SECRET`

---

### FASE 4: First Deploy Test

**Ir a Render Dashboard → Tu Web Service:**

1. Click **"Manual Deploy"** o espera auto-deploy desde GitHub
2. Monitorear logs en **"Logs"** tab
3. **Esperar ~2-3 minutos** hasta que diga "Your service is live"

**Obtener tu URL pública:**  
`https://espejo-fantasma-api.onrender.com`

---

### FASE 5: Endpoint Testing (TERMINAL LOCAL)

**Ejecuta estos curl tests para validar:**

```powershell
# Test 1: Health check
curl -X GET "https://espejo-fantasma-api.onrender.com/ping"

# Test 2: Get Stripe key
curl -X GET "https://espejo-fantasma-api.onrender.com/api/stripe-key"

# Test 3: Get pricing
curl -X GET "https://espejo-fantasma-api.onrender.com/api/pricing"

# Test 4: Create payment intent
curl -X POST "https://espejo-fantasma-api.onrender.com/api/payment-intent" \
  -H "Content-Type: application/json" \
  -d '{
    "couple_id": "test_session_123",
    "plan": "premium",
    "user_email": "test@example.com",
    "analysis_data": {}
  }'

# Test 5: Initialize blind session
curl -X POST "https://espejo-fantasma-api.onrender.com/blind-session/init?couple_id=test_123&client_ip=127.0.0.1&client_ua=test"

# Test 6: Get metrics
curl -X GET "https://espejo-fantasma-api.onrender.com/metrics"
```

**Resultados esperados:**
- ✅ /ping → `{"status": "ok", ...}`
- ✅ /api/stripe-key → `{"publishableKey": "pk_test_..."}`
- ✅ /api/pricing → Pricing cards data
- ✅ /api/payment-intent → `{"client_secret": "pi_...", ...}`
- ✅ /blind-session/init → Tokens para usuarios A y B
- ✅ /metrics → Session counts

---

### FASE 6: Frontend Wiring (LOCAL)

**Actualizar `frontend_couple_interface_STRIPE_SUPREMO.html`:**

En el inicio del script, cambiar:

```javascript
// ANTES (localhost):
const API_BASE = "http://localhost:8000";

// DESPUÉS (Render):
const API_BASE = "https://espejo-fantasma-api.onrender.com";
```

**Servir frontend localmente para testing:**
```powershell
# Usar Python simple server
python -m http.server 8080 --directory "C:\Users\javie\OneDrive\Escritorio\diagnostico financiero"

# Abrir: http://localhost:8080/frontend_couple_interface_STRIPE_SUPREMO.html
```

---

### FASE 7: Database Migration (AUTOMÁTICO)

**Render ejecutará automáticamente:**
```
pip install -r requirements.txt
python migrate.py  # Auto-creates tables
```

Si necesitas verificar manualmente:
```powershell
# Conectarse a PostgreSQL remoto (instalar psql client si no lo tienes)
psql postgresql://postgres:PASSWORD@HOST:5432/diagnostico_prod
```

---

## ✅ VALIDACIÓN FINAL

Una vez todo esté deployado, verificar:

- [ ] Git repo public en GitHub
- [ ] Web Service "Live" en Render
- [ ] PostgreSQL "Available" en Render
- [ ] Todos los 6 endpoints responden correctamente
- [ ] Frontend se conecta a API remota
- [ ] Stripe test keys funcionan
- [ ] Webhooks reciben eventos (verificar en Stripe Dashboard)

---

## 🚀 SIGUIENTE PASO DESPUÉS DE SPRINT 5

**SPRINT 9 — A/B Testing:**
- Segmentar usuarios (50% SUPREMO, 50% Control)
- Trackear conversion rates, payment time, NPS
- Validar 91% psychological anchor premium selection

---

## 📞 DEBUGGING

Si algo falla:

```powershell
# Ver logs en tiempo real:
# Ir a Render Dashboard → Tu servicio → "Logs" tab

# Verificar env vars en Render:
# Ir a "Environment" tab

# Ver Database status:
# Ir a PostgreSQL → "Info" tab → External Database URL

# Test Stripe webhooks:
# https://dashboard.stripe.com/webhooks → Select tu endpoint → "Logs"
```

---

## ⏱️ TIEMPO ESTIMADO

- Fase 1 (Git): 2 minutos
- Fase 2 (Render setup): 10 minutos
- Fase 3 (Env vars): 5 minutos
- Fase 4 (Deploy): 3 minutos
- Fase 5 (Testing): 5 minutos
- **Total: ~25 minutos**

---

**Status after completion:** Ready for SPRINT 9 (A/B Testing)  
**Current:** AWAITING YOUR ACTION — Tu ejecución de Fase 1 desbloquea todo.

Mejor perfecto que bueno: ✅ Arquitectura completada. Ahora necesito que DEPLIEGUES.

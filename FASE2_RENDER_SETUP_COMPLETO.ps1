# ═══════════════════════════════════════════════════════════════════════════════
# FASE 2 — RENDER DEPLOYMENT COMPLETO
# Instrucciones exactas para Render Dashboard
# TOP 1% MUNDIAL — LISTO PARA COPIAR-PEGAR
# ═══════════════════════════════════════════════════════════════════════════════

# ⚠️ ESTO VA EN EL NAVEGADOR EN https://dashboard.render.com
# NO es un script PowerShell — son pasos manuales en la UI

<#
═══════════════════════════════════════════════════════════════════════════════
PASO 1A: CREATE POSTGRESQL DATABASE
═══════════════════════════════════════════════════════════════════════════════

1. Ve a https://dashboard.render.com
2. Click "New +" en la esquina superior
3. Selecciona "PostgreSQL"
4. Rellena:
   - Name: diagnostico-db
   - Database: diagnostico_prod
   - User: postgres
   - Region: Frankfurt (EU)
   - Plan: Free (o Starter si quieres mejor uptime)
5. Click "Create Database"
6. ESPERA 2-3 minutos hasta que diga "Available"
7. COPIAR EXACTO estos datos:

   External Database URL: postgresql://postgres:PASSWORD@render-hostname:5432/diagnostico_prod
   (GUARDAR en notepad, lo necesitarás en Paso 2B)

═══════════════════════════════════════════════════════════════════════════════
PASO 1B: CREATE WEB SERVICE
═══════════════════════════════════════════════════════════════════════════════

1. Click "New +" nuevamente
2. Selecciona "Web Service"
3. En "Repository", conecta tu GitHub:
   - Si es primera vez, authoriza Render en GitHub
   - Selecciona: diagnostico-financiero
4. Rellena el formulario:
   Name: espejo-fantasma-api
   Environment: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: uvicorn app_couple_endpoints:app --host 0.0.0.0 --port $PORT
   Plan: Free
5. NO HAGAS CLICK EN CREATE TODAVÍA — scroll down a "Environment"

═══════════════════════════════════════════════════════════════════════════════
PASO 1C: ENVIRONMENT VARIABLES (CRÍTICO)
═══════════════════════════════════════════════════════════════════════════════

En la sección "Environment" del Web Service, agrega EXACTAMENTE esto:

KEY                          VALUE
──────────────────────────────────────────────────────────────────────────
DATABASE_URL                 postgresql://postgres:PASSWORD@render-host:5432/diagnostico_prod
                             (COPIAR DEL PASO 1A exacto)

STRIPE_API_KEY               sk_test_51234567890ABCDEFGH
                             (De https://dashboard.stripe.com/apikeys → Secret key)

STRIPE_PUBLISHABLE_KEY       pk_test_51234567890ABCDEFGH
                             (De https://dashboard.stripe.com/apikeys → Publishable key)

STRIPE_WEBHOOK_SECRET        whsec_1234567890ABCDEFGH
                             (De https://dashboard.stripe.com/webhooks → Signing secret)

JWT_SECRET                   tu-secret-aleatorio-super-largo-min-32-chars-importante

LOG_LEVEL                    info

PYTHONUNBUFFERED             1

═══════════════════════════════════════════════════════════════════════════════
PASO 2: OBTENER STRIPE KEYS (https://dashboard.stripe.com)
═══════════════════════════════════════════════════════════════════════════════

🔑 API Keys:
   Ve a: https://dashboard.stripe.com/apikeys
   - Copiar "Secret key" (empieza con sk_test_) → STRIPE_API_KEY
   - Copiar "Publishable key" (empieza con pk_test_) → STRIPE_PUBLISHABLE_KEY

🔔 Webhook Secret:
   Ve a: https://dashboard.stripe.com/webhooks
   - Click "Add an endpoint"
   - URL: https://espejo-fantasma-api.onrender.com/webhooks/stripe
   - Events to send:
     ☑ payment_intent.succeeded
     ☑ payment_intent.payment_failed
     ☑ charge.refunded
   - Click "Create endpoint"
   - Copiar "Signing secret" (whsec_...) → STRIPE_WEBHOOK_SECRET

═══════════════════════════════════════════════════════════════════════════════
PASO 3: CREAR WEB SERVICE EN RENDER
═══════════════════════════════════════════════════════════════════════════════

1. Vuelve al formulario de Web Service
2. VERIFICA que todas las env vars están correctas
3. Click "Create Web Service"
4. ESPERA deploy (2-3 minutos)
5. Cuando diga "Your service is live", nota la URL:
   https://espejo-fantasma-api.onrender.com

═══════════════════════════════════════════════════════════════════════════════
PASO 4: VALIDAR ENDPOINTS (PowerShell)
═══════════════════════════════════════════════════════════════════════════════

Cuando Render diga "Live", ejecuta en PowerShell:

curl -X GET "https://espejo-fantasma-api.onrender.com/ping"
curl -X GET "https://espejo-fantasma-api.onrender.com/api/stripe-key"
curl -X GET "https://espejo-fantasma-api.onrender.com/api/pricing"
curl -X POST "https://espejo-fantasma-api.onrender.com/blind-session/init?couple_id=test123&client_ip=127.0.0.1&client_ua=test"

Resultados esperados:
✅ /ping → {"status": "ok", "timestamp": "..."}
✅ /api/stripe-key → {"publishableKey": "pk_test_..."}
✅ /api/pricing → {pricing context JSON}
✅ /blind-session/init → {"couple_id": "...", "token_a": "...", "token_b": "..."}

═══════════════════════════════════════════════════════════════════════════════
PASO 5: ACTUALIZAR FRONTEND (LOCAL)
═══════════════════════════════════════════════════════════════════════════════

En: C:\Users\javie\OneDrive\Escritorio\diagnostico financiero\
     frontend_couple_interface_STRIPE_SUPREMO.html

Busca esta línea (al inicio del <script>):
   const API_BASE = "http://localhost:8000";

CAMBIA A:
   const API_BASE = "https://espejo-fantasma-api.onrender.com";

Guarda archivo. Listo.

═══════════════════════════════════════════════════════════════════════════════
STATUS CHECKLIST
═══════════════════════════════════════════════════════════════════════════════

Cuando TODO esté hecho, verifica:

☐ GitHub repo tiene commits (https://github.com/TU_USERNAME/diagnostico-financiero)
☐ Render PostgreSQL está "Available"
☐ Render Web Service está "Live"
☐ /ping responde con status ok
☐ /api/stripe-key devuelve publishableKey
☐ Stripe test keys agregadas en Render
☐ Webhook configurado en Stripe
☐ Frontend apunta a https://espejo-fantasma-api.onrender.com

Cuando TODO está ☑ → SPRINT 5 COMPLETO
Siguiente: SPRINT 9 (A/B Testing)

═══════════════════════════════════════════════════════════════════════════════
#>

echo "✅ GUÍA COMPLETA LISTA"
echo "Abre esta guía en notepad o refresca tu navegador en:"
echo "https://dashboard.render.com"

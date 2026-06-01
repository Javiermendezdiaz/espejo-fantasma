# ═══════════════════════════════════════════════════════════════════════════════
# SPRINT 5 — GIT + RENDER DEPLOY
# Ejecutar en PowerShell local (NO en sandbox)
# Ubicación: C:\Users\javie\OneDrive\Escritorio\diagnostico financiero\
# Tiempo: ~5 minutos
# ═══════════════════════════════════════════════════════════════════════════════

# PASO 1: Navigate a carpeta (ejecutar en tu terminal local)
cd "C:\Users\javie\OneDrive\Escritorio\diagnostico financiero\"

# PASO 2: Verificar que git está instalado
git --version

# PASO 3: Inicializar repositorio (PRIMERA VEZ SOLO)
git init

# PASO 4: Agregar remote (REEMPLAZA TU_USERNAME con tu GitHub username)
# Ejemplo: git remote add origin https://github.com/javier-mendez/diagnostico-financiero.git
git remote add origin https://github.com/TU_USERNAME/diagnostico-financiero.git

# PASO 5: Agregar todos los archivos
git add .

# PASO 6: Hacer commit
git commit -m "SPRINT 8 SUPREMO: Stripe integration + 6 IxD mechanics + Psychological pricing — TOP 1% MUNDIAL"

# PASO 7: Push a GitHub (primera vez usa --set-upstream)
git push -u origin main

# ═══════════════════════════════════════════════════════════════════════════════
# DESPUÉS DE GIT: Ir a https://dashboard.render.com y seguir FASE 2 del guide
# ═══════════════════════════════════════════════════════════════════════════════

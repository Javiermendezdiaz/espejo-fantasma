# SPRINT 5 PHASE 1 — GIT INITIALIZATION + GITHUB PUSH

**ESTADO:** Ready for manual execution on Windows Terminal

**POR QUÉ MANUAL:**
El sandbox Linux tiene limitaciones con paths que contienen espacios. La solución:
ejecutar estos comandos en tu máquina Windows usando Git Bash o PowerShell nativa.

---

## Paso 1 — Abrir Terminal en el directorio del proyecto

```powershell
cd "C:\Users\javie\OneDrive\Escritorio\diagnostico financiero"
```

---

## Paso 2 — Inicializar Git repo

```bash
git init
git config user.name "Javier Méndez"
git config user.email "javier@mendezconsultoria.com"
git add .
git commit -m "SPRINT 4: Production deployment infrastructure — 18 files ready for Render deployment"
```

**Verificar:**
```bash
git log --oneline
```
Debe mostrar 1 commit.

---

## Paso 3 — Crear repositorio en GitHub

1. Ve a https://github.com/new
2. Nombre: `diagnostico-fantasma` (o `diagnostico-financiero-parejas`)
3. Descripción: "Espejo Fantasma — Diagnóstico Financiero de Parejas con FastAPI, PostgreSQL, ReportLab"
4. Visibilidad: **Private** (datos financieros sensibles)
5. **NO inicializar** con README (ya tienes archivos locales)
6. Crear repositorio

---

## Paso 4 — Conectar origin y push

Después de crear en GitHub, copiar el HTTPS URL de clonación y ejecutar:

```bash
git remote add origin https://github.com/[TU_USUARIO]/diagnostico-fantasma.git
git branch -M main
git push -u origin main
```

**Verificar en GitHub:**
- Debe aparecer TODOS los 18 archivos en `main` branch
- Incluye: requirements.txt, Procfile, docker-compose.yml, migrate.py, Dockerfile, etc.

---

## Paso 5 — Configurar secrets para CI/CD en GitHub

En GitHub → Settings → Secrets and variables → Actions → New repository secret

Añadir SOLO estos dos (Render setup ocurre después):
- **RENDER_SERVICE_ID**: (obtener después de crear Web Service en Render)
- **RENDER_API_KEY**: (de tu cuenta Render)

---

## ✅ FIN PHASE 1

Cuando GitHub esté listo con todos los 18 archivos en `main`, avisa y pasamos a:
**SPRINT 5 PHASE 2 — Crear Render Web Service + PostgreSQL managed**

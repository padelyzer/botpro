# ☁️ BotphIA en Google Cloud Platform - Guía Completa

## 🎁 **Tier Gratuito de GCP**

### **$300 USD en créditos gratis por 90 días** para nuevas cuentas
- ✅ Cloud Run: 2 millones de requests/mes gratis
- ✅ App Engine: 28 horas instancia/día gratis
- ✅ Cloud Storage: 5GB gratis
- ✅ Firestore: 1GB gratis

---

## 🚀 **CONFIGURACIÓN INICIAL**

### **Paso 1: Activar Billing (Para obtener los $300)**

1. Ve a: https://console.cloud.google.com/billing
2. Click "Add billing account"
3. Selecciona "Individual" 
4. Ingresa tarjeta (NO se cobra, solo validación)
5. Automáticamente recibes $300 USD en créditos

### **Paso 2: Configurar Proyecto**

Ya creamos el proyecto `botphia-trading-pro`. Ahora desde la terminal:

```bash
# Verificar proyecto activo
gcloud config get-value project
# Debe mostrar: botphia-trading-pro

# Ligar billing account al proyecto
gcloud billing accounts list
# Copia el ACCOUNT_ID

# Vincular
gcloud billing projects link botphia-trading-pro \
  --billing-account=TU_ACCOUNT_ID
```

---

## 🎯 **OPCIÓN 1: Cloud Run (Recomendado)**

### **Ventajas:**
- ✅ Escala automática a 0 (no pagas cuando no se usa)
- ✅ WebSocket nativo
- ✅ 2 millones requests/mes gratis
- ✅ HTTPS automático

### **Deploy Directo:**

```bash
# 1. Habilitar APIs
gcloud services enable run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com

# 2. Deploy desde código fuente
cd /Users/ja/saby/trading_api

gcloud run deploy botphia-dashboard \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1 \
  --max-instances 3
```

### **Resultado:**
```
✅ URL: https://botphia-dashboard-xxxxx-uc.a.run.app/pro
```

---

## 🎯 **OPCIÓN 2: App Engine (Más Gratis)**

### **Ventajas:**
- ✅ 28 horas instancia/día gratis SIEMPRE
- ✅ No requiere contenedores
- ✅ Más simple de configurar

### **Deploy:**

```bash
# 1. Habilitar App Engine
gcloud app create --region=us-central

# 2. Deploy
cd /Users/ja/saby/trading_api
gcloud app deploy

# 3. Ver la app
gcloud app browse
```

### **Resultado:**
```
✅ URL: https://botphia-trading-pro.appspot.com/pro
```

---

## 🐳 **OPCIÓN 3: Cloud Run con Docker**

Si prefieres usar Docker:

```bash
# 1. Build imagen
docker build -f Dockerfile.web -t gcr.io/botphia-trading-pro/botphia:latest .

# 2. Push a Container Registry
docker push gcr.io/botphia-trading-pro/botphia:latest

# 3. Deploy
gcloud run deploy botphia-dashboard \
  --image gcr.io/botphia-trading-pro/botphia:latest \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8888
```

---

## 📋 **COMANDOS ÚTILES**

### **Verificar Estado:**
```bash
# Ver servicios de Cloud Run
gcloud run services list

# Ver logs
gcloud run services logs botphia-dashboard

# Ver métricas
gcloud monitoring metrics-descriptors list
```

### **Actualizar Aplicación:**
```bash
# Hacer cambios y re-deploy
gcloud run deploy botphia-dashboard --source .

# O para App Engine
gcloud app deploy
```

### **Custom Domain:**
```bash
# Verificar dominio
gcloud domains verify tu-dominio.com

# Mapear a Cloud Run
gcloud run domain-mappings create \
  --service botphia-dashboard \
  --domain tu-dominio.com \
  --region us-central1
```

---

## 💰 **COSTOS ESTIMADOS**

### **Con Tier Gratuito (Primeros 90 días):**
- **$0** - Cubierto por los $300 de crédito

### **Después del Tier Gratuito:**

#### **Cloud Run:**
- 2M requests/mes: **GRATIS**
- 360,000 GB-segundos/mes: **GRATIS**
- 180,000 vCPU-segundos/mes: **GRATIS**
- **Costo estimado:** $0-5/mes para uso moderado

#### **App Engine:**
- 28 horas instancia F1/día: **GRATIS**
- 1GB salida/día: **GRATIS**
- **Costo estimado:** $0 si no excedes límites

---

## ⚡ **DEPLOY RÁPIDO (Copy & Paste)**

### **Si ya tienes billing activado:**

```bash
# Todo en 3 comandos
cd /Users/ja/saby/trading_api

# Habilitar APIs
gcloud services enable run.googleapis.com

# Deploy
gcloud run deploy botphia-dashboard \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080

# ¡Listo! Tu URL aparecerá al final
```

---

## 🔧 **TROUBLESHOOTING**

### **Error: Billing not enabled**
```bash
# Verificar billing
gcloud billing accounts list

# Si no aparece ninguna, ve a:
# https://console.cloud.google.com/billing
```

### **Error: APIs not enabled**
```bash
# Habilitar todas las APIs necesarias
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  containerregistry.googleapis.com \
  artifactregistry.googleapis.com
```

### **Error: Permission denied**
```bash
# Verificar roles
gcloud projects get-iam-policy botphia-trading-pro

# Agregar rol de owner a tu cuenta
gcloud projects add-iam-policy-binding botphia-trading-pro \
  --member="user:k.oncito@gmail.com" \
  --role="roles/owner"
```

---

## ✅ **CHECKLIST DE DEPLOYMENT**

- [ ] Crear cuenta GCP nueva
- [ ] Activar billing (para obtener $300)
- [ ] Crear proyecto `botphia-trading-pro`
- [ ] Habilitar APIs necesarias
- [ ] Deploy a Cloud Run o App Engine
- [ ] Verificar que funciona el dashboard
- [ ] Configurar dominio personalizado (opcional)

---

## 🎉 **RESULTADO FINAL**

### **URLs de tu Dashboard:**

```bash
# Cloud Run
https://botphia-dashboard-xxxxx-uc.a.run.app/pro

# App Engine  
https://botphia-trading-pro.appspot.com/pro

# Con dominio personalizado
https://dashboard.tu-dominio.com/pro
```

### **Características:**
- ✅ Dashboard profesional estilo Binance
- ✅ Terminal de monitoreo en vivo
- ✅ WebSocket funcionando
- ✅ SSL/HTTPS automático
- ✅ Escala automática
- ✅ $300 USD de crédito gratis

---

## 💡 **SIGUIENTE PASO INMEDIATO**

1. **Activa billing en:** https://console.cloud.google.com/billing
2. **Ejecuta estos comandos:**

```bash
# Verificar billing
gcloud billing accounts list

# Si aparece tu cuenta, deploy directo:
cd /Users/ja/saby/trading_api
gcloud run deploy botphia-dashboard --source . --region us-central1 --allow-unauthenticated
```

**¡En 5 minutos tendrás BotphIA corriendo en Google Cloud!** 🚀
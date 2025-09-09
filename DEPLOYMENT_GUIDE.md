# 🚀 BOTPHIA - GUÍA DE DEPLOYMENT

## 📋 Tabla de Contenidos
1. [Requisitos del Sistema](#requisitos-del-sistema)
2. [Instalación Inicial](#instalación-inicial)
3. [Operación Continua 24/7](#operación-continua-247)
4. [Monitoreo y Supervisión](#monitoreo-y-supervisión)
5. [Mantenimiento](#mantenimiento)
6. [Solución de Problemas](#solución-de-problemas)

---

## 🔧 Requisitos del Sistema

### Hardware Mínimo
- CPU: 2 cores
- RAM: 4 GB
- Disco: 20 GB libres
- Conexión a Internet estable

### Software Requerido
- Python 3.8+
- Node.js 16+
- npm o yarn
- Git

### Dependencias Python
```bash
pip3 install -r requirements.txt
```

### Dependencias Node.js
```bash
cd botphia && npm install
```

---

## 📦 Instalación Inicial

### 1. Clonar el Repositorio
```bash
git clone [repository-url]
cd saby
```

### 2. Configurar Variables de Entorno
```bash
# En trading_api/.env
BINANCE_API_KEY=tu_api_key
BINANCE_API_SECRET=tu_api_secret
DATABASE_URL=sqlite:///trading_bot.db
```

### 3. Preparar la Base de Datos
```bash
cd trading_api
python3 -c "from database import init_db; init_db()"
```

### 4. Verificar Instalación
```bash
./check_status.sh
```

---

## 🤖 Operación Continua 24/7

### Método 1: Script de Producción (Recomendado)

#### Iniciar Sistema Completo
```bash
cd /Users/ja/saby/trading_api
chmod +x start_production.sh
./start_production.sh
```

Este script:
- ✅ Verifica todas las dependencias
- ✅ Construye el frontend para producción
- ✅ Inicia la API backend (puerto 8000)
- ✅ Inicia el sistema de trading continuo
- ✅ Sirve el frontend (puerto 5173)
- ✅ Guarda PIDs para gestión

#### Detener Sistema
```bash
./stop_production.sh
```

#### Verificar Estado
```bash
./check_status.sh
```

### Método 2: SystemD Service (Linux/macOS)

#### Instalar como Servicio
```bash
# Copiar archivo de servicio
sudo cp trading_bot.service /etc/systemd/system/

# Recargar systemd
sudo systemctl daemon-reload

# Habilitar inicio automático
sudo systemctl enable trading_bot.service

# Iniciar servicio
sudo systemctl start trading_bot.service
```

#### Comandos de Gestión
```bash
# Ver estado
sudo systemctl status trading_bot

# Detener
sudo systemctl stop trading_bot

# Reiniciar
sudo systemctl restart trading_bot

# Ver logs
sudo journalctl -u trading_bot -f
```

### Método 3: Proceso Manual con Supervisor

#### Archivo run_system.py
El sistema incluye un gestor completo que:
- 🚀 Inicia generador de señales
- 🧹 Mantenimiento automático de BD (cada hora)
- 🔔 Monitor de alertas (cada 30 segundos)
- 🏥 Health checks (cada minuto)
- 🔄 Auto-reinicio en caso de fallas (máx 5 intentos)

```bash
cd trading_api
python3 run_system.py
```

---

## 📊 Monitoreo y Supervisión

### Dashboard de Monitoreo
```bash
./check_status.sh
```

Muestra:
- Estado de procesos (API, Trading System, Frontend)
- Estadísticas del sistema
- Uso de recursos (CPU, RAM, Disco)
- Últimas líneas de logs
- Alertas y avisos

### Logs en Tiempo Real
```bash
# Ver todos los logs
tail -f logs/trading_system.log

# Solo errores
tail -f logs/error.log | grep ERROR

# Señales de alta calidad
tail -f logs/trading_system.log | grep "Alta Calidad"
```

### Alertas Automáticas
El sistema genera alertas para:
- Señales con confianza ≥ 80%
- Errores críticos del sistema
- Problemas de conectividad con Binance
- Uso excesivo de recursos

---

## 🔧 Mantenimiento

### Rotación de Logs

#### Configuración Automática
```bash
# Añadir a crontab
0 0 * * * /Users/ja/saby/trading_api/rotate_logs.sh
```

#### Rotación Manual
```bash
./rotate_logs.sh
```

### Backups Automáticos

#### Configurar Backup Diario
```bash
# Añadir a crontab
0 2 * * * /Users/ja/saby/trading_api/backup_system.sh
```

#### Backup Manual
```bash
./backup_system.sh
```

El backup incluye:
- Bases de datos SQLite
- Configuraciones del sistema
- Estados del trading bot
- Logs recientes
- Scripts de deployment

### Limpieza de Base de Datos
Se ejecuta automáticamente cada hora, pero puede forzarse:
```bash
python3 -c "from database_maintenance import DatabaseMaintenance; m = DatabaseMaintenance(); m.run_maintenance()"
```

---

## 🔥 Solución de Problemas

### Sistema No Inicia

1. **Verificar puertos**
```bash
# Verificar puerto 8000 (API)
lsof -i :8000

# Verificar puerto 5173 (Frontend)
lsof -i :5173
```

2. **Limpiar procesos zombies**
```bash
pkill -f "fastapi_server"
pkill -f "signal_generator"
pkill -f "run_system"
```

3. **Verificar permisos**
```bash
chmod +x *.sh
```

### API No Responde

1. **Verificar logs**
```bash
tail -50 logs/api.log
tail -50 logs/error.log
```

2. **Reiniciar API**
```bash
pkill -f "uvicorn"
cd trading_api
python3 -m uvicorn fastapi_server:app --reload --port 8000
```

### Señales No Se Generan

1. **Verificar generador**
```bash
ps aux | grep signal_generator
```

2. **Verificar conexión Binance**
```bash
curl -s https://api.binance.com/api/v3/ping
```

3. **Reiniciar generador**
```bash
pkill -f "signal_generator"
python3 signal_generator.py
```

### Base de Datos Corrupta

1. **Hacer backup**
```bash
cp trading_bot.db trading_bot.db.backup
```

2. **Verificar integridad**
```bash
sqlite3 trading_bot.db "PRAGMA integrity_check;"
```

3. **Reparar si es necesario**
```bash
sqlite3 trading_bot.db ".recover" | sqlite3 trading_bot_recovered.db
mv trading_bot_recovered.db trading_bot.db
```

---

## 📈 Optimización de Performance

### Reducir Uso de CPU
```python
# En trading_config.py
SCAN_INTERVAL = 60  # Aumentar intervalo
MAX_CONCURRENT_REQUESTS = 3  # Reducir concurrencia
```

### Reducir Uso de Memoria
```python
# En signal_generator.py
MAX_SIGNALS_IN_MEMORY = 1000  # Limitar señales en memoria
CACHE_EXPIRY = 300  # Reducir tiempo de cache
```

### Optimizar Base de Datos
```bash
# Vacuum y reindex periódicamente
sqlite3 trading_bot.db "VACUUM;"
sqlite3 trading_bot.db "REINDEX;"
```

---

## 🔐 Seguridad

### Proteger API Keys
```bash
# Nunca commitear .env
echo ".env" >> .gitignore

# Permisos restrictivos
chmod 600 .env
```

### Limitar Acceso a API
```python
# En fastapi_server.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
)
```

### Backup de Seguridad
```bash
# Backup encriptado
tar -czf - backup_dir | openssl enc -aes-256-cbc -salt -out backup.tar.gz.enc
```

---

## 📞 Soporte y Contacto

### Logs de Debug
Para activar modo debug:
```python
# En run_system.py
logging.basicConfig(level=logging.DEBUG)
```

### Comandos Útiles
```bash
# Estado completo del sistema
./check_status.sh

# Reinicio rápido
./stop_production.sh && ./start_production.sh

# Ver procesos del sistema
ps aux | grep -E "(trading|signal|fastapi)"

# Espacio en disco
df -h /Users/ja/saby

# Conexiones de red
netstat -an | grep -E "(8000|5173)"
```

---

## 🎯 Checklist de Deployment

- [ ] Instalar dependencias Python
- [ ] Instalar dependencias Node.js
- [ ] Configurar variables de entorno
- [ ] Inicializar base de datos
- [ ] Ejecutar tests de conectividad
- [ ] Configurar rotación de logs
- [ ] Configurar backups automáticos
- [ ] Iniciar sistema con `start_production.sh`
- [ ] Verificar con `check_status.sh`
- [ ] Configurar monitoreo continuo
- [ ] Documentar configuración específica

---

## 📅 Mantenimiento Programado

### Diario
- Rotación de logs (automático)
- Verificación de alertas

### Semanal
- Backup completo del sistema
- Revisión de performance
- Actualización de dependencias menores

### Mensual
- Vacuum de base de datos
- Análisis de logs de error
- Revisión de seguridad
- Actualización de documentación

---

## 🏁 Conclusión

El sistema BotphIA está diseñado para operar de forma continua 24/7 con mínima supervisión. Los scripts de gestión automatizan la mayoría de tareas de mantenimiento y el sistema incluye auto-recuperación ante fallos.

**Accesos principales:**
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs
- Monitoreo: `./check_status.sh`

Para operación óptima, asegúrate de:
1. Mantener los logs rotados
2. Realizar backups regulares
3. Monitorear el uso de recursos
4. Actualizar dependencias periódicamente

¡El sistema está listo para operar continuamente!
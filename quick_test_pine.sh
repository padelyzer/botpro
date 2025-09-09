#!/bin/bash

# Script rápido para probar el sistema de Pine Script

echo "🚀 TEST RÁPIDO - SISTEMA PINE SCRIPT"
echo "===================================="

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Paso 1: Limpiar archivos antiguos de prueba
echo -e "\n${YELLOW}1. Limpiando archivos antiguos...${NC}"
rm -f /tmp/*test*.pine 2>/dev/null
echo "   ✅ Limpieza completada"

# Paso 2: Ejecutar prueba de generación
echo -e "\n${YELLOW}2. Probando generador de Pine Script...${NC}"
python3 test_pinescript_generation.py > /tmp/test_output.log 2>&1

if [ $? -eq 0 ]; then
    echo -e "   ${GREEN}✅ Generador funcionando correctamente${NC}"
    
    # Mostrar archivos generados
    echo -e "\n${YELLOW}3. Archivos Pine Script generados:${NC}"
    ls -la /tmp/*.pine 2>/dev/null | tail -5
    
    # Mostrar el último archivo generado
    LATEST_FILE=$(ls -t /tmp/*.pine 2>/dev/null | head -1)
    
    if [ ! -z "$LATEST_FILE" ]; then
        echo -e "\n${YELLOW}4. Preview del último Pine Script:${NC}"
        echo "   Archivo: $LATEST_FILE"
        echo "   ----------------------------------------"
        head -n 30 "$LATEST_FILE"
        echo "   ..."
        echo "   ----------------------------------------"
        
        # Copiar al portapapeles si es Mac
        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo -e "\n${YELLOW}5. Copiando al portapapeles...${NC}"
            cat "$LATEST_FILE" | pbcopy
            echo -e "   ${GREEN}✅ Pine Script copiado al portapapeles${NC}"
            echo "   📋 Puedes pegarlo directamente en TradingView"
        fi
        
        echo -e "\n${BLUE}📊 INSTRUCCIONES RÁPIDAS:${NC}"
        echo "   1. Abre TradingView.com"
        echo "   2. Abre Pine Editor (botón inferior o Cmd+E)"
        echo "   3. Pega el código (Cmd+V)"
        echo "   4. Click 'Add to Chart'"
        
        echo -e "\n${GREEN}✅ TEST COMPLETADO EXITOSAMENTE${NC}"
        echo -e "\n📁 Archivo disponible en: ${LATEST_FILE}"
    else
        echo -e "   ${RED}❌ No se encontraron archivos Pine Script${NC}"
    fi
else
    echo -e "   ${RED}❌ Error en la generación${NC}"
    echo "   Ver log: /tmp/test_output.log"
    tail -20 /tmp/test_output.log
fi

echo -e "\n===================================="
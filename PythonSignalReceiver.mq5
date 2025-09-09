//+------------------------------------------------------------------+
//|                                        PythonSignalReceiver.mq5  |
//|                                  Copyright 2024, Trading System  |
//|                                         Recibe señales de Python |
//+------------------------------------------------------------------+
#property copyright "Trading System 2024"
#property version   "1.00"
#property description "Expert Advisor que recibe señales de Python y ejecuta trades"

// Inputs del EA
input string   InpServerAddress = "127.0.0.1";  // Dirección del servidor Python
input int      InpServerPort = 9999;            // Puerto del servidor
input double   InpLotSize = 0.01;               // Tamaño de lote por defecto
input int      InpMagicNumber = 234000;         // Magic number
input int      InpSlippage = 30;                // Slippage permitido
input bool     InpAutoTrade = true;             // Trading automático activado

// Variables globales
int socket = INVALID_HANDLE;
string receivedSignal = "";

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   // Verificar que el trading automático esté permitido
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED))
   {
      Print("❌ Trading automático no permitido. Active AutoTrading.");
      return(INIT_FAILED);
   }
   
   // Verificar conexión con el broker
   if(!TerminalInfoInteger(TERMINAL_CONNECTED))
   {
      Print("❌ No conectado al broker");
      return(INIT_FAILED);
   }
   
   Print("✅ Python Signal Receiver EA iniciado");
   Print("   Esperando señales en ", InpServerAddress, ":", InpServerPort);
   
   // Configurar timer para revisar señales cada segundo
   EventSetTimer(1);
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   
   if(socket != INVALID_HANDLE)
   {
      SocketClose(socket);
   }
   
   Print("EA detenido. Razón: ", reason);
}

//+------------------------------------------------------------------+
//| Timer function - Revisa señales cada segundo                     |
//+------------------------------------------------------------------+
void OnTimer()
{
   // Intentar conectar si no está conectado
   if(socket == INVALID_HANDLE)
   {
      ConnectToPython();
   }
   
   // Leer señales si está conectado
   if(socket != INVALID_HANDLE)
   {
      ReadSignal();
   }
}

//+------------------------------------------------------------------+
//| Conectar con servidor Python                                     |
//+------------------------------------------------------------------+
bool ConnectToPython()
{
   socket = SocketCreate();
   
   if(socket == INVALID_HANDLE)
   {
      Print("❌ Error creando socket");
      return false;
   }
   
   if(!SocketConnect(socket, InpServerAddress, InpServerPort, 1000))
   {
      SocketClose(socket);
      socket = INVALID_HANDLE;
      return false;
   }
   
   Print("✅ Conectado al servidor Python");
   return true;
}

//+------------------------------------------------------------------+
//| Leer señal del socket                                           |
//+------------------------------------------------------------------+
void ReadSignal()
{
   char buffer[];
   int bytesRead = SocketRead(socket, buffer, 1024, 100);
   
   if(bytesRead > 0)
   {
      string signal = CharArrayToString(buffer, 0, bytesRead);
      ProcessSignal(signal);
   }
   else if(bytesRead < 0)
   {
      // Error de conexión
      Print("❌ Conexión perdida con Python");
      SocketClose(socket);
      socket = INVALID_HANDLE;
   }
}

//+------------------------------------------------------------------+
//| Procesar señal JSON recibida                                     |
//+------------------------------------------------------------------+
void ProcessSignal(string jsonSignal)
{
   Print("📨 Señal recibida: ", jsonSignal);
   
   // Parser JSON simple (para señales básicas)
   string symbol = GetJsonValue(jsonSignal, "symbol");
   string action = GetJsonValue(jsonSignal, "action");
   double stopLoss = StringToDouble(GetJsonValue(jsonSignal, "stop_loss"));
   double takeProfit = StringToDouble(GetJsonValue(jsonSignal, "take_profit"));
   
   // Convertir símbolo si es necesario
   symbol = ConvertSymbol(symbol);
   
   // Verificar que el símbolo existe
   if(!SymbolSelect(symbol, true))
   {
      Print("❌ Símbolo no encontrado: ", symbol);
      return;
   }
   
   // Ejecutar trade si el auto trading está activado
   if(InpAutoTrade)
   {
      ExecuteTrade(symbol, action, stopLoss, takeProfit);
   }
   else
   {
      // Solo mostrar alerta
      Alert("Señal: ", action, " ", symbol, " SL:", stopLoss, " TP:", takeProfit);
   }
}

//+------------------------------------------------------------------+
//| Ejecutar trade basado en la señal                               |
//+------------------------------------------------------------------+
bool ExecuteTrade(string symbol, string action, double sl, double tp)
{
   MqlTradeRequest request = {};
   MqlTradeResult result = {};
   
   // Obtener información del símbolo
   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
   
   // Configurar request
   request.symbol = symbol;
   request.volume = InpLotSize;
   request.magic = InpMagicNumber;
   request.deviation = InpSlippage;
   
   if(action == "BUY")
   {
      request.type = ORDER_TYPE_BUY;
      request.price = ask;
      
      // Calcular SL y TP si no se especifican
      if(sl == 0) sl = ask - 100 * point;  // 100 pips por defecto
      if(tp == 0) tp = ask + 200 * point;  // 200 pips por defecto
   }
   else if(action == "SELL")
   {
      request.type = ORDER_TYPE_SELL;
      request.price = bid;
      
      if(sl == 0) sl = bid + 100 * point;
      if(tp == 0) tp = bid - 200 * point;
   }
   else
   {
      Print("❌ Acción no válida: ", action);
      return false;
   }
   
   request.sl = NormalizeDouble(sl, digits);
   request.tp = NormalizeDouble(tp, digits);
   request.action = TRADE_ACTION_DEAL;
   request.type_filling = ORDER_FILLING_IOC;
   request.comment = "Python Signal";
   
   // Enviar orden
   if(!OrderSend(request, result))
   {
      Print("❌ Error ejecutando trade: ", result.comment);
      return false;
   }
   
   Print("✅ Trade ejecutado: ", symbol, " ", action, " Ticket: ", result.order);
   
   // Enviar confirmación a Python
   SendConfirmation(result.order);
   
   return true;
}

//+------------------------------------------------------------------+
//| Convertir símbolo de Python a formato MT5                       |
//+------------------------------------------------------------------+
string ConvertSymbol(string symbol)
{
   // Agregar sufijos según el broker
   if(StringFind(symbol, "USD") < 0 && StringFind(symbol, "USDT") < 0)
   {
      symbol = symbol + "USD";  // O "USDT" según tu broker
   }
   
   // Conversiones específicas
   StringReplace(symbol, "BTC", "BTCUSD");
   StringReplace(symbol, "ETH", "ETHUSD");
   StringReplace(symbol, "DOGE", "DOGEUSD");
   
   return symbol;
}

//+------------------------------------------------------------------+
//| Parser JSON simple                                              |
//+------------------------------------------------------------------+
string GetJsonValue(string json, string key)
{
   int keyPos = StringFind(json, "\"" + key + "\"");
   if(keyPos < 0) return "";
   
   int colonPos = StringFind(json, ":", keyPos);
   if(colonPos < 0) return "";
   
   int valueStart = colonPos + 1;
   while(StringGetCharacter(json, valueStart) == ' ' || 
         StringGetCharacter(json, valueStart) == '"')
   {
      valueStart++;
   }
   
   int valueEnd = valueStart;
   while(valueEnd < StringLen(json) && 
         StringGetCharacter(json, valueEnd) != ',' &&
         StringGetCharacter(json, valueEnd) != '}' &&
         StringGetCharacter(json, valueEnd) != '"')
   {
      valueEnd++;
   }
   
   return StringSubstr(json, valueStart, valueEnd - valueStart);
}

//+------------------------------------------------------------------+
//| Enviar confirmación a Python                                     |
//+------------------------------------------------------------------+
void SendConfirmation(ulong ticket)
{
   if(socket != INVALID_HANDLE)
   {
      string confirmation = StringFormat("{\"status\":\"executed\",\"ticket\":%d}", ticket);
      char buffer[];
      StringToCharArray(confirmation, buffer);
      SocketSend(socket, buffer, ArraySize(buffer));
   }
}

//+------------------------------------------------------------------+
//| Función para gestión de posiciones abiertas                     |
//+------------------------------------------------------------------+
void ManageOpenPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionSelectByTicket(PositionGetTicket(i)))
      {
         if(PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
         {
            double profit = PositionGetDouble(POSITION_PROFIT);
            double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
            double currentPrice = PositionGetDouble(POSITION_PRICE_CURRENT);
            double sl = PositionGetDouble(POSITION_SL);
            
            // Trailing stop simple
            if(profit > 0)
            {
               double newSl = 0;
               if(PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY)
               {
                  newSl = currentPrice - 50 * _Point;
                  if(newSl > sl)
                  {
                     ModifyPosition(PositionGetTicket(i), newSl, PositionGetDouble(POSITION_TP));
                  }
               }
               else
               {
                  newSl = currentPrice + 50 * _Point;
                  if(newSl < sl || sl == 0)
                  {
                     ModifyPosition(PositionGetTicket(i), newSl, PositionGetDouble(POSITION_TP));
                  }
               }
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Modificar posición                                              |
//+------------------------------------------------------------------+
bool ModifyPosition(ulong ticket, double sl, double tp)
{
   MqlTradeRequest request = {};
   MqlTradeResult result = {};
   
   request.action = TRADE_ACTION_SLTP;
   request.position = ticket;
   request.sl = NormalizeDouble(sl, _Digits);
   request.tp = NormalizeDouble(tp, _Digits);
   
   return OrderSend(request, result);
}

//+------------------------------------------------------------------+
//| OnTick - Se ejecuta en cada tick del mercado                    |
//+------------------------------------------------------------------+
void OnTick()
{
   // Gestionar posiciones abiertas
   ManageOpenPositions();
}
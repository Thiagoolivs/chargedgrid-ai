# Demonstração de memória conversacional — Sprint 03

Requisito 3.2: memória por sessão usando os recursos do framework, com pelo menos 3 turnos de interação.

Gerado por `python evals/demo_memoria.py` em 2026-09-21 04:06:33.

---

### Caso M01 — memoria

- **Modelo:** `google/gemini-3.6-flash`
- **thread_id:** `demo-M01` (o mesmo nos 3 turnos)
- **Esperado:** responde 12 e cita Solar Park

**Turno 1 — usuário**

> Estou utilizando um carregador no condomínio Solar Park.

**Turno 1 — agente** · rota `conversa` · 2.56s

```
Entendido! Registrei que você está utilizando o carregador no condomínio **Solar Park**. 

Como posso ajudar você com o seu carregador GoodWe HCA-G2 hoje? Se precisar de suporte técnico, configurações de carregamento, autenticação ou troubleshooting, é só me falar!
```

**Turno 2 — usuário**

> Existem 12 vagas de carregamento.

**Turno 2 — agente** · rota `conversa` · 3.14s

```
Anotado! O local conta com **12 vagas de carregamento**. 

Como posso ajudar você com os carregadores GoodWe HCA-G2 nessas vagas? Se precisar de orientações sobre gestão de carga, monitoramento, autenticação por RFID ou configurações do sistema, estou à disposição!
```

**Turno 3 — usuário**

> Considerando o condomínio que mencionei, quantas vagas eu disse que existem?

**Turno 3 — agente** · rota `conversa` · 2.06s

```
Você mencionou que existem **12 vagas** de carregamento no condomínio Solar Park.
```

**Memória do framework:** o checkpointer acumulou **6 mensagens** para este `thread_id` (3 turnos de usuário + as respostas). Nenhuma lista de histórico é mantida pelo código da aplicação — o estado vem do `MemorySaver` do LangGraph.

---

### Caso M02 — memoria

- **Modelo:** `google/gemini-3.6-flash`
- **thread_id:** `demo-M02` (o mesmo nos 3 turnos)
- **Esperado:** GW22K-HCA-20 e Modbus TCP

**Turno 1 — usuário**

> Tenho um GW22K-HCA-20 instalado.

**Turno 1 — agente** · rota `conversa` · 3.86s

```
[RESPOSTA DIRETA]
Entendido. Registro que você possui o modelo GoodWe GW22K-HCA-20 (trifásico, potência nominal de 22 kW) instalado.

---

[COMO FUNCIONA]
Este modelo opera em rede trifásica e permite o carregamento de veículos elétricos em potências de até 22 kW, podendo ser gerenciado localmente via aplicativo SolarGo (conexão Bluetooth) ou remotamente via SEMS Portal (Nuvem), além de suportar integração via Modbus TCP com inversores GoodWe compatíveis (linhas ET, SDT, ES, EHB, EH Plus, ESA).

---

[DETALHES TECNICOS]
- Modelo: GW22K-HCA-20
- Tipo de rede: Trifásico
- Potência nominal: 22 kW
- Conectividade de configuração: Bluetooth (SolarGo) / Wi-Fi / LAN (SEMS Portal)
- Protocolo de integração: Modbus TCP

---

[PROXIMO PASSO]
Como posso ajudar com o seu GW22K-HCA-20? Você precisa de auxílio com modos de carregamento, configurações de comunicação, monitoramento ou troubleshooting?
```

**Turno 2 — usuário**

> Ele está conectado a um inversor GoodWe via Modbus TCP.

**Turno 2 — agente** · rota `conversa` · 4.44s

```
[RESPOSTA DIRETA]
Entendido. O seu carregador GW22K-HCA-20 (22 kW, trifásico) está integrado ao seu inversor GoodWe através do protocolo de comunicação Modbus TCP em rede local.

---

[COMO FUNCIONA]
A conexão via Modbus TCP permite a troca de dados em tempo real entre o inversor GoodWe e o carregador HCA-G2. Isso habilita o gerenciamento inteligente de energia, permitindo que o carregador ajuste sua potência dinamicamente com base na geração solar disponível, no estado de carga da bateria (SOC) e no consumo da residência, otimizando o uso da energia fotovoltaica.

---

[DETALHES TECNICOS]
- Protocolo: Modbus TCP
- Interface física de rede: Conexão via cabo de rede (LAN / Ethernet) na mesma rede local (subnet) do inversor.
- Comunicação de controle: Troca de registradores de leitura e escrita para comandos de início/parada, ajuste de limite de corrente e leitura de parâmetros operacionais.
- Inversores compatíveis: Linhas GoodWe ET, SDT, ES, EHB, EH Plus e ESA.

---

[PROXIMO PASSO]
Você gostaria de configurar um modo de carregamento específico (como PV Priority ou Fast Charging), ajustar parâmetros de corrente/potência ou precisa verificar a conectividade dos registradores Modbus?
```

**Turno 3 — usuário**

> Qual modelo eu disse que tenho e por qual protocolo ele se comunica?

**Turno 3 — agente** · rota `conversa` · 2.29s

```
Você informou que possui o modelo **GW22K-HCA-20** (22 kW, trifásico) e que ele está conectado ao inversor via protocolo **Modbus TCP**.
```

**Memória do framework:** o checkpointer acumulou **6 mensagens** para este `thread_id` (3 turnos de usuário + as respostas). Nenhuma lista de histórico é mantida pelo código da aplicação — o estado vem do `MemorySaver` do LangGraph.

---

### Caso M03 — memoria

- **Modelo:** `google/gemini-3.6-flash`
- **thread_id:** `demo-M03` (o mesmo nos 3 turnos)
- **Esperado:** 40 carros/dia e janela 18h-21h

**Turno 1 — usuário**

> Meu eletroposto atende 40 carros por dia.

**Turno 1 — agente** · rota `conversa` · 2.26s

```
Anotado! Você opera um eletroposto com uma demanda considerável de 40 veículos por dia. 

Como posso ajudar na gestão ou configuração técnica dos seus carregadores GoodWe HCA-G2 para atender a esse fluxo?
```

**Turno 2 — usuário**

> O horário de pico é das 18h às 21h.

**Turno 2 — agente** · rota `conversa` · 2.61s

```
Compreendido. O seu horário de pico é das 18h às 21h, com um fluxo diário total de 40 veículos.

Como posso ajudar você a otimizar o carregamento, a comunicação ou o controle de demanda dos seus carregadores GoodWe HCA-G2 para esse período?
```

**Turno 3 — usuário**

> Com base no que informei, resuma meu cenário de operação.

**Turno 3 — agente** · rota `conversa` · 2.37s

```
Com base nas informações que você compartilhou, o seu cenário de operação é:

- **Volume diário:** Atendimento de 40 veículos elétricos por dia.
- **Horário de pico:** Concentração de demanda entre 18h e 21h.

Se precisar de auxílio com a configuração dos carregadores GoodWe HCA-G2 para gerenciar a potência ou os modos de carga nesse intervalo, fico à disposição!
```

**Memória do framework:** o checkpointer acumulou **6 mensagens** para este `thread_id` (3 turnos de usuário + as respostas). Nenhuma lista de histórico é mantida pelo código da aplicação — o estado vem do `MemorySaver` do LangGraph.

---

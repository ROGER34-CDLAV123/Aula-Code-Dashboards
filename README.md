# Dashboard de RH + Agente de IA Gemini

Este projeto é um dashboard interativo para gestão de Recursos Humanos, desenvolvido em Python com Streamlit, integrando KPIs, gráficos, filtros avançados e um chatbot Gemini 2.5 Flash para suporte inteligente.

## Principais Funcionalidades
- **Visual moderno:** Tema escuro, roxo e cinza, com cards e layout responsivo.
- **KPIs de RH:** Headcount, desligados, folha salarial, custo total, idade média, avaliação média.
- **Gráficos dinâmicos:** Headcount por área, salário médio por cargo, distribuição de idade, tempo de casa, status, sexo, avaliação média por área/cargo.
- **Filtros avançados:** Sidebar com múltiplos filtros (área, cargo, nível, sexo, status, nome, idade, salário, datas).
- **Exportação de dados:** Download dos dados filtrados em CSV ou Excel.
- **Agente de IA Gemini:** Chatbot integrado, interface customizada, histórico de mensagens, resposta em tempo real via API Gemini 2.5 Flash.

## Como rodar
1. **Crie o ambiente virtual:**
   ```powershell
   python -m venv app.venv
   .\app.venv\Scripts\Activate.ps1
   ```
2. **Instale as dependências:**
   ```powershell
   pip install -r requirements.txt
   ```
3. **Configure a chave Gemini:**
   - Crie uma variável de ambiente `GEMINI_API_KEY` com sua chave Gemini.
   - No Windows PowerShell:
     ```powershell
     $env:GEMINI_API_KEY = "SUA_CHAVE_AQUI"
     ```
4. **Execute o dashboard:**
   ```powershell
   streamlit run app.py
   ```

## Estrutura
- `app.py` — Código principal do dashboard e chatbot.
- `BaseFuncionarios.xlsx` — Base de dados exemplo para RH.
- `requirements.txt` — Dependências do projeto.
- `app.venv/` — Ambiente virtual Python.

## Personalização
- Cores, layout e KPIs podem ser facilmente ajustados no código.
- O chatbot pode ser adaptado para outros modelos de IA.

## Dúvidas ou sugestões?
Abra o dashboard, clique no botão **Agente de IA** e converse com o Gemini!

---
Projeto feito com 💜 por Code Academy.

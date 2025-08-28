# app.py — Dashboard de RH (versão ajustada com tratamento de erros visível)
# Como rodar:
# 0) Crie um ambiente virtual  ->  python -m venv venv
# 1) Ative a venv  ->  .venv\Scripts\Activate.ps1   (Windows)  |  source .venv/bin/activate  (Mac/Linux)
# 2) Instale deps  ->  pip install -r requirements.txt
# 3) Rode          ->  streamlit run app.py

import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import date
import requests
import json

# Inicializa o histórico do chat se não existir
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --------------------- Configuração básica ---------------------
st.set_page_config(
    page_title="Dashboard de RH",
    layout="wide",
    initial_sidebar_state="expanded"
)
# Estilo customizado para fundo escuro e cores profissionais
st.markdown(
    """
    <style>
    body, .stApp {
        background-color: #181820;
        color: #e0e0e0;
    }
    .css-1d391kg, .css-1v0mbdj, .stSidebar {
        background: #232336 !important;
        color: #e0e0e0 !important;
    }
    .stButton>button, .stDownloadButton>button {
        background-color: #6c3fcf !important;
        color: #fff !important;
        border-radius: 8px;
        border: none;
    }
    .stDataFrame, .stTable {
        background: #232336 !important;
        color: #e0e0e0 !important;
    }
    .stMetric {
        background: #232336 !important;
        color: #e0e0e0 !important;
        border-radius: 10px;
        padding: 10px;
        box-shadow: 0 2px 8px #0002;
    }
    .stExpander {
        background: #232336 !important;
        color: #e0e0e0 !important;
    }
    .stSlider .rc-slider-track {
        background: #6c3fcf !important;
    }
    .stSlider .rc-slider-handle {
        border-color: #6c3fcf !important;
    }
    .stTextInput>div>input {
        background: #232336 !important;
        color: #e0e0e0 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)
st.title("Dashboard de RH")

# Se o arquivo estiver na mesma pasta do app.py, pode deixar assim.
# Ajuste para o caminho local caso esteja em outra pasta (ex.: r"C:\...\BaseFuncionarios.xlsx")
DEFAULT_EXCEL_PATH = "BaseFuncionarios.xlsx"
DATE_COLS = ["Data de Nascimento", "Data de Contratacao", "Data de Demissao"]

# --------------------- Funções utilitárias ---------------------
def brl(x: float) -> str:
    try:
        return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"

def prepare_df(df: pd.DataFrame) -> pd.DataFrame:
    # Padroniza textos
    for c in df.select_dtypes(include="object").columns:
        df[c] = df[c].astype(str).str.strip()

    # Datas
    for c in DATE_COLS:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], dayfirst=True, errors="coerce")

    # Padroniza Sexo
    if "Sexo" in df.columns:
        df["Sexo"] = (
            df["Sexo"].str.upper()
            .replace({"MASCULINO": "M", "FEMININO": "F"})
        )

    # Garante numéricos
    for col in ["Salario Base", "Impostos", "Beneficios", "VT", "VR"]:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # Colunas derivadas
    today = pd.Timestamp(date.today())

    if "Data de Nascimento" in df.columns:
        df["Idade"] = ((today - df["Data de Nascimento"]).dt.days // 365).clip(lower=0)

    if "Data de Contratacao" in df.columns:
        meses = (today.year - df["Data de Contratacao"].dt.year) * 12 + \
                (today.month - df["Data de Contratacao"].dt.month)
        df["Tempo de Casa (meses)"] = meses.clip(lower=0)

    if "Data de Demissao" in df.columns:
        df["Status"] = np.where(df["Data de Demissao"].notna(), "Desligado", "Ativo")
    else:
        df["Status"] = "Ativo"

    df["Custo Total Mensal"] = df[["Salario Base", "Impostos", "Beneficios", "VT", "VR"]].sum(axis=1)
    return df

@st.cache_data
def load_from_path(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=0, engine="openpyxl")
    return prepare_df(df)

@st.cache_data
def load_from_bytes(uploaded_bytes) -> pd.DataFrame:
    df = pd.read_excel(uploaded_bytes, sheet_name=0, engine="openpyxl")
    return prepare_df(df)

# --------------------- Funções de KPIs ---------------------
def k_headcount_ativo(df):
    if "Status" in df.columns:
        return int((df["Status"] == "Ativo").sum())
    return 0

def k_desligados(df):
    if "Status" in df.columns:
        return int((df["Status"] == "Desligado").sum())
    return 0

def k_folha(df):
    if "Salario Base" in df.columns and "Status" in df.columns:
        return float(df.loc[df["Status"] == "Ativo", "Salario Base"].sum())
    return 0.0

def k_custo_total(df):
    if "Custo Total Mensal" in df.columns and "Status" in df.columns:
        return float(df.loc[df["Status"] == "Ativo", "Custo Total Mensal"].sum())
    return 0.0

def k_idade_media(df):
    if "Idade" in df.columns and not df["Idade"].dropna().empty:
        return float(df["Idade"].mean())
    return 0.0

def k_avaliacao_media(df):
    if "Avaliação" in df.columns and not df["Avaliação"].dropna().empty:
        return float(df["Avaliação"].mean())
    return 0.0

# --------------------- Sidebar: fonte de dados ---------------------
with st.sidebar:
    st.header("Fonte de dados")
    st.caption("Use **Upload** ou informe o caminho do arquivo .xlsx")
    up = st.file_uploader("Carregar Excel (.xlsx)", type=["xlsx"])
    caminho_manual = st.text_input("Ou caminho do Excel", value=DEFAULT_EXCEL_PATH)
    st.divider()
    if up is None:
        existe = os.path.exists(caminho_manual)
        st.write(f"Arquivo em caminho: **{caminho_manual}**")
        st.write("Existe: ", "✅ Sim" if existe else "❌ Não")

# --------------------- Carregamento com erros visíveis ---------------------
df = None
fonte = None
if up is not None:
    try:
        df = load_from_bytes(up)
        fonte = "Upload"
    except Exception as e:
        st.error(f"Erro ao ler Excel (Upload): {e}")
        st.stop()
else:
    try:
        if not os.path.exists(caminho_manual):
            st.error(f"Arquivo não encontrado em: {caminho_manual}")
            st.info("Dica: coloque o .xlsx na mesma pasta do app.py ou ajuste o caminho acima.")
            st.stop()
        df = load_from_path(caminho_manual)
        fonte = "Caminho"
    except Exception as e:
        st.error(f"Erro ao ler Excel (Caminho): {e}")
        st.stop()

st.caption(f"Dados carregados via **{fonte}**. Linhas: {len(df)} | Colunas: {len(df.columns)}")

# Mostra colunas detectadas (ajuda no debug)
with st.expander("Ver colunas detectadas"):
    st.write(list(df.columns))

# --------------------- Filtros ---------------------
st.sidebar.header("Filtros")

def msel(col_name: str):
    if col_name in df.columns:
        vals = sorted([v for v in df[col_name].dropna().unique()])
        return st.sidebar.multiselect(col_name, vals)
    return []

area_sel   = msel("Área")
nivel_sel  = msel("Nível")
cargo_sel  = msel("Cargo")
sexo_sel   = msel("Sexo")
status_sel = msel("Status")
nome_busca = st.sidebar.text_input("Buscar por Nome Completo", key="nome_busca_simple")

# Períodos
def date_bounds(series: pd.Series):
    s = series.dropna()
    if s.empty:
        return None
    return (s.min().date(), s.max().date())

contr_bounds = date_bounds(df["Data de Contratacao"]) if "Data de Contratacao" in df.columns else None
demis_bounds = date_bounds(df["Data de Demissao"]) if "Data de Demissao" in df.columns else None

if contr_bounds:
    d1, d2 = st.sidebar.date_input("Período de Contratação", value=contr_bounds, key="basic_periodo_contratacao")
else:
    d1, d2 = None, None

if demis_bounds:
    d3, d4 = st.sidebar.date_input("Período de Demissão", value=demis_bounds, key="basic_periodo_demissao")
else:
    d3, d4 = None, None

# Sliders (idade e salário)
if "Idade" in df.columns and not df["Idade"].dropna().empty:
    ida_min, ida_max = int(df["Idade"].min()), int(df["Idade"].max())
    faixa_idade = st.sidebar.slider("Faixa Etária", ida_min, ida_max, (ida_min, ida_max), key="basic_faixa_idade")
else:
    faixa_idade = None

if "Salario Base" in df.columns and not df["Salario Base"].dropna().empty:
    sal_min, sal_max = float(df["Salario Base"].min()), float(df["Salario Base"].max())
    faixa_sal = st.sidebar.slider("Faixa de Salário Base", float(sal_min), float(sal_max), (float(sal_min), float(sal_max)), key="basic_faixa_sal")
else:
    faixa_sal = None

# Aplica filtros
df_f = df.copy()

def apply_in(df_, col, values):
    if values and col in df_.columns:
        return df_[df_[col].isin(values)]
    return df_

df_f = apply_in(df_f, "Área", area_sel)
df_f = apply_in(df_f, "Nível", nivel_sel)
df_f = apply_in(df_f, "Cargo", cargo_sel)
df_f = apply_in(df_f, "Sexo", sexo_sel)
df_f = apply_in(df_f, "Status", status_sel)

if nome_busca and "Nome Completo" in df_f.columns:
    df_f = df_f[df_f["Nome Completo"].str.contains(nome_busca, case=False, na=False)]

if faixa_idade and "Idade" in df_f.columns:
    df_f = df_f[(df_f["Idade"] >= faixa_idade[0]) & (df_f["Idade"] <= faixa_idade[1])]

if faixa_sal and "Salario Base" in df_f.columns:
    df_f = df_f[(df_f["Salario Base"] >= faixa_sal[0]) & (df_f["Salario Base"] <= faixa_sal[1])]

if d1 and d2 and "Data de Contratacao" in df_f.columns:
    df_f = df_f[(df_f["Data de Contratacao"].isna()) |
                ((df_f["Data de Contratacao"] >= pd.to_datetime(d1)) &
                 (df_f["Data de Contratacao"] <= pd.to_datetime(d2)))]

if d3 and d4 and "Data de Demissao" in df_f.columns:
    df_f = df_f[(df_f["Data de Demissao"].isna()) |
                ((df_f["Data de Demissao"] >= pd.to_datetime(d3)) &
                 (df_f["Data de Demissao"] <= pd.to_datetime(d4)))]

# --------------------- Filtros Avançados ---------------------
st.sidebar.header("Filtros Avançados")

# Filtro por área
if "Área" in df.columns:
    area_filtrada = st.sidebar.multiselect("Filtrar por Área", options=sorted(df["Área"].dropna().unique()))
else:
    area_filtrada = []

# Filtro por cargo
if "Cargo" in df.columns:
    cargo_filtrado = st.sidebar.multiselect("Filtrar por Cargo", options=sorted(df["Cargo"].dropna().unique()))
else:
    cargo_filtrado = []

# Filtro por nível
if "Nível" in df.columns:
    nivel_filtrado = st.sidebar.multiselect("Filtrar por Nível", options=sorted(df["Nível"].dropna().unique()))
else:
    nivel_filtrado = []

# Filtro por sexo
if "Sexo" in df.columns:
    sexo_filtrado = st.sidebar.multiselect("Filtrar por Sexo", options=sorted(df["Sexo"].dropna().unique()))
else:
    sexo_filtrado = []

# Filtro por status
if "Status" in df.columns:
    status_filtrado = st.sidebar.multiselect("Filtrar por Status", options=sorted(df["Status"].dropna().unique()))
else:
    status_filtrado = []

# Filtro por nome
if "Nome Completo" in df.columns:
    nome_filtrado = st.sidebar.text_input("Buscar por Nome Completo", key="nome_filtrado_advanced")
else:
    nome_filtrado = ""

# Filtro por faixa etária
if "Idade" in df.columns and not df["Idade"].dropna().empty:
    idade_min, idade_max = int(df["Idade"].min()), int(df["Idade"].max())
    faixa_idade = st.sidebar.slider("Faixa Etária", idade_min, idade_max, (idade_min, idade_max), key="faixa_idade_advanced")
else:
    faixa_idade = None

# Filtro por faixa salarial
if "Salario Base" in df.columns and not df["Salario Base"].dropna().empty:
    sal_min, sal_max = float(df["Salario Base"].min()), float(df["Salario Base"].max())
    faixa_sal = st.sidebar.slider("Faixa de Salário Base", sal_min, sal_max, (sal_min, sal_max), key="faixa_sal_advanced")
else:
    faixa_sal = None

# Filtro por período de contratação
if "Data de Contratacao" in df.columns:
    contr_min, contr_max = df["Data de Contratacao"].min(), df["Data de Contratacao"].max()
    periodo_contratacao = st.sidebar.date_input("Período de Contratação", (contr_min, contr_max), key="advanced_periodo_contratacao")
else:
    periodo_contratacao = None

# Filtro por período de demissão
if "Data de Demissao" in df.columns:
    demis_min, demis_max = df["Data de Demissao"].min(), df["Data de Demissao"].max()
    periodo_demissao = st.sidebar.date_input("Período de Demissão", (demis_min, demis_max), key="advanced_periodo_demissao")
else:
    periodo_demissao = None

# Aplica os filtros ao DataFrame
filtered_df = df.copy()
if area_filtrada:
    filtered_df = filtered_df[filtered_df["Área"].isin(area_filtrada)]
if cargo_filtrado:
    filtered_df = filtered_df[cargo_filtrado]
if nivel_filtrado:
    filtered_df = filtered_df[nivel_filtrado]
if sexo_filtrado:
    filtered_df = filtered_df[sexo_filtrado]
if status_filtrado:
    filtered_df = filtered_df[status_filtrado]
if nome_filtrado:
    filtered_df = filtered_df[filtered_df["Nome Completo"].str.contains(nome_filtrado, case=False, na=False)]
if faixa_idade and "Idade" in filtered_df.columns:
    filtered_df = filtered_df[(filtered_df["Idade"] >= faixa_idade[0]) & (filtered_df["Idade"] <= faixa_idade[1])]
if faixa_sal and "Salario Base" in filtered_df.columns:
    filtered_df = filtered_df[(filtered_df["Salario Base"] >= faixa_sal[0]) & (filtered_df["Salario Base"] <= faixa_sal[1])]
if periodo_contratacao and "Data de Contratacao" in filtered_df.columns:
    d1, d2 = periodo_contratacao
    filtered_df = filtered_df[(filtered_df["Data de Contratacao"].isna()) |
        ((filtered_df["Data de Contratacao"] >= pd.to_datetime(d1)) & (filtered_df["Data de Contratacao"] <= pd.to_datetime(d2)))]
if periodo_demissao and "Data de Demissao" in filtered_df.columns:
    d3, d4 = periodo_demissao
    filtered_df = filtered_df[(filtered_df["Data de Demissao"].isna()) |
        ((filtered_df["Data de Demissao"] >= pd.to_datetime(d3)) & (filtered_df["Data de Demissao"] <= pd.to_datetime(d4)))]

# --------------------- KPIs ---------------------
kpi_style = """
    <style>
    .kpi-card {
        background: #232336;
        color: #e0e0e0;
        border-radius: 18px; /* Arredondamento mais sutil */
        box-shadow: 0 2px 8px #0002;
        padding: 18px 10px;
        margin: 0 8px;
        text-align: center;
        font-size: 1.2em;
        min-width: 120px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .kpi-label {
        color: #b39ddb;
        font-size: 0.95em;
        margin-bottom: 4px;
    }
    .kpi-value {
        color: #6c3fcf;
        font-size: 1.5em;
        font-weight: bold;
    }
    </style>
"""

st.markdown(kpi_style, unsafe_allow_html=True)

# Faixa de KPIs em cards, dois por linha
kpi_row1 = st.columns(2)
kpi_row1[0].markdown(f"""
    <div class='kpi-card' style='width:100%;margin-bottom:18px;'>
        <div class='kpi-label'>Headcount Ativo</div>
        <div class='kpi-value'>{k_headcount_ativo(filtered_df)}</div>
    </div>
""", unsafe_allow_html=True)
kpi_row1[1].markdown(f"""
    <div class='kpi-card' style='width:100%;margin-bottom:18px;'>
        <div class='kpi-label'>Desligados</div>
        <div class='kpi-value'>{k_desligados(filtered_df)}</div>
    </div>
""", unsafe_allow_html=True)

kpi_row2 = st.columns(2)
kpi_row2[0].markdown(f"""
    <div class='kpi-card' style='width:100%;margin-bottom:18px;'>
        <div class='kpi-label'>Folha Salarial</div>
        <div class='kpi-value'>{brl(k_folha(filtered_df))}</div>
    </div>
""", unsafe_allow_html=True)
kpi_row2[1].markdown(f"""
    <div class='kpi-card' style='width:100%;margin-bottom:18px;'>
        <div class='kpi-label'>Custo Total</div>
        <div class='kpi-value'>{brl(k_custo_total(filtered_df))}</div>
    </div>
""", unsafe_allow_html=True)

kpi_row3 = st.columns(2)
kpi_row3[0].markdown(f"""
    <div class='kpi-card' style='width:100%;margin-bottom:18px;'>
        <div class='kpi-label'>Idade Média</div>
        <div class='kpi-value'>{k_idade_media(filtered_df):.1f} anos</div>
    </div>
""", unsafe_allow_html=True)
kpi_row3[1].markdown(f"""
    <div class='kpi-card' style='width:100%;margin-bottom:18px;'>
        <div class='kpi-label'>Avaliação Média</div>
        <div class='kpi-value'>{k_avaliacao_media(filtered_df):.2f}</div>
    </div>
""", unsafe_allow_html=True)

st.divider()

# --------------------- Botão Agente de IA ---------------------
if 'show_ia_input' not in st.session_state:
    st.session_state['show_ia_input'] = False

col_ia = st.columns([1,6,1])
with col_ia[1]:
    if st.button('Agente de IA', use_container_width=True):
        st.session_state['show_ia_input'] = True

if st.session_state['show_ia_input']:
    st.markdown("""
        <style>
        .ia-row { display: flex; align-items: center; width: 100%; }
        .ia-input {
            flex: 1;
            height: 38px;
            border-radius: 10px;
            border: 1px solid #6c3fcf;
            padding: 0 16px;
            font-size: 1.1em;
            background: #232336;
            color: #e0e0e0;
            margin-right: 10px;
        }
        .ia-send {
            height: 38px;
            background: #1976d2;
            color: #fff;
            border: none;
            border-radius: 10px;
            padding: 0 24px;
            font-size: 1.1em;
            font-weight: bold;
            cursor: pointer;
            box-shadow: 0 2px 8px #0002;
        }
        .ia-history {
            width: 100%;
            min-height: 570px;
            max-height: 570px;
            background: #232336;
            color: #e0e0e0;
            border-radius: 10px;
            border: 1px solid #6c3fcf;
            margin-bottom: 12px;
            padding: 18px 16px;
            overflow-y: auto;
            font-size: 1.08em;
        }
        .ia-msg-user { color: #b39ddb; margin-bottom: 8px; }
        .ia-msg-ia { color: #6c3fcf; margin-bottom: 8px; }
        </style>
    """, unsafe_allow_html=True)
    # Caixa de histórico/mensagens
    history_html = "<div class='ia-history'>"
    if st.session_state.chat_history:
        for msg in st.session_state.chat_history:
            if msg['role'] == 'user':
                history_html += f"<div class='ia-msg-user'><b>Você:</b> {msg['content']}</div>"
            else:
                history_html += f"<div class='ia-msg-ia'><b>IA:</b> {msg['content']}</div>"
    else:
        history_html += "<span style='color:#888'>Nenhuma mensagem ainda.</span>"
    history_html += "</div>"
    st.markdown(history_html, unsafe_allow_html=True)
    # Caixa de texto + botão enviar
    with st.form(key='ia_form', clear_on_submit=True):
        ia_col1, ia_col2 = st.columns([8,2])
        user_msg = ia_col1.text_input('Mensagem para IA', label_visibility='collapsed', key='ia_input')
        send_btn = ia_col2.form_submit_button('Enviar', use_container_width=True)
        if send_btn and user_msg.strip():
            st.session_state.chat_history.append({'role': 'user', 'content': user_msg})
            # Gemini API
            GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
            if not GEMINI_API_KEY:
                ia_response = 'Configure a variável de ambiente GEMINI_API_KEY com sua chave Gemini.'
            else:
                with st.spinner('A IA está pensando...'):
                    try:
                        url = 'https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash-latest:generateContent?key=' + GEMINI_API_KEY
                        headers = {'Content-Type': 'application/json'}
                        payload = {
                            'contents': [
                                {'parts': [{'text': user_msg}]}
                            ]
                        }
                        r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
                        if r.status_code == 200:
                            resp = r.json()
                            ia_response = resp['candidates'][0]['content']['parts'][0]['text'] if 'candidates' in resp else 'Resposta não encontrada.'
                        else:
                            ia_response = f'Erro Gemini: {r.status_code} - {r.text}'
                    except requests.Timeout:
                        ia_response = 'Tempo excedido. Tente novamente ou verifique sua conexão.'
                    except Exception as e:
                        ia_response = f'Erro de conexão Gemini: {e}'
            st.session_state.chat_history.append({'role': 'ia', 'content': ia_response})

st.divider()

# --------------------- Gráficos RH recomendados ---------------------
graf_row1 = st.columns(3)
with graf_row1[0]:
    if "Área" in filtered_df.columns:
        d = filtered_df.groupby("Área").size().reset_index(name="Headcount")
        if not d.empty:
            fig = px.bar(
                d, x="Área", y="Headcount", title="Headcount por Área",
                color_discrete_sequence=["#6c3fcf"],
                template="plotly_dark"
            )
            fig.update_layout(
                plot_bgcolor="#232336", paper_bgcolor="#232336",
                font_color="#e0e0e0", title_font_color="#b39ddb"
            )
            st.plotly_chart(fig, use_container_width=True)
with graf_row1[1]:
    if "Cargo" in filtered_df.columns and "Salario Base" in filtered_df.columns:
        d = filtered_df.groupby("Cargo", as_index=False)["Salario Base"].mean().sort_values("Salario Base", ascending=False)
        if not d.empty:
            fig = px.bar(
                d, x="Cargo", y="Salario Base", title="Salário Médio por Cargo",
                color_discrete_sequence=["#b39ddb"],
                template="plotly_dark"
            )
            fig.update_layout(
                plot_bgcolor="#232336", paper_bgcolor="#232336",
                font_color="#e0e0e0", title_font_color="#6c3fcf"
            )
            st.plotly_chart(fig, use_container_width=True)
with graf_row1[2]:
    if "Status" in filtered_df.columns:
        d = filtered_df["Status"].value_counts().reset_index()
        d.columns = ["Status", "Contagem"]
        if not d.empty:
            fig = px.pie(
                d, values="Contagem", names="Status", title="Ativos x Desligados",
                color_discrete_sequence=["#6c3fcf", "#b39ddb", "#232336"],
                template="plotly_dark"
            )
            fig.update_layout(
                plot_bgcolor="#232336", paper_bgcolor="#232336",
                font_color="#e0e0e0", title_font_color="#b39ddb"
            )
            st.plotly_chart(fig, use_container_width=True)

graf_row2 = st.columns(3)
with graf_row2[0]:
    if "Idade" in filtered_df.columns and not filtered_df["Idade"].dropna().empty:
        fig = px.histogram(
            filtered_df, x="Idade", nbins=20, title="Distribuição de Idade",
            color_discrete_sequence=["#6c3fcf"],
            template="plotly_dark"
        )
        fig.update_layout(
            plot_bgcolor="#232336", paper_bgcolor="#232336",
            font_color="#e0e0e0", title_font_color="#b39ddb"
        )
        st.plotly_chart(fig, use_container_width=True)
with graf_row2[1]:
    if "Tempo de Casa (meses)" in filtered_df.columns and not filtered_df["Tempo de Casa (meses)"].dropna().empty:
        fig = px.histogram(
            filtered_df, x="Tempo de Casa (meses)", nbins=20, title="Tempo de Casa (meses)",
            color_discrete_sequence=["#b39ddb"],
            template="plotly_dark"
        )
        fig.update_layout(
            plot_bgcolor="#232336", paper_bgcolor="#232336",
            font_color="#e0e0e0", title_font_color="#6c3fcf"
        )
        st.plotly_chart(fig, use_container_width=True)
with graf_row2[2]:
    if "Sexo" in filtered_df.columns:
        d = filtered_df["Sexo"].value_counts().reset_index()
        d.columns = ["Sexo", "Contagem"]
        if not d.empty:
            fig = px.pie(
                d, values="Contagem", names="Sexo", title="Distribuição por Sexo",
                color_discrete_sequence=["#6c3fcf", "#b39ddb", "#232336"],
                template="plotly_dark"
            )
            fig.update_layout(
                plot_bgcolor="#232336", paper_bgcolor="#232336",
                font_color="#e0e0e0", title_font_color="#b39ddb"
            )
            st.plotly_chart(fig, use_container_width=True)

# Avaliação média por área/cargo
if "Avaliação" in filtered_df.columns:
    st.markdown("<h4 style='color:#b39ddb;'>Avaliação Média por Área/Cargo</h4>", unsafe_allow_html=True)
    graf_row3 = st.columns(2)
    with graf_row3[0]:
        if "Área" in filtered_df.columns:
            d = filtered_df.groupby("Área", as_index=False)["Avaliação"].mean().sort_values("Avaliação", ascending=False)
            if not d.empty:
                fig = px.bar(
                    d, x="Área", y="Avaliação", title="Avaliação Média por Área",
                    color_discrete_sequence=["#6c3fcf"],
                    template="plotly_dark"
                )
                fig.update_layout(
                    plot_bgcolor="#232336", paper_bgcolor="#232336",
                    font_color="#e0e0e0", title_font_color="#b39ddb"
                )
                st.plotly_chart(fig, use_container_width=True)
    with graf_row3[1]:
        if "Cargo" in filtered_df.columns:
            d = filtered_df.groupby("Cargo", as_index=False)["Avaliação"].mean().sort_values("Avaliação", ascending=False)
            if not d.empty:
                fig = px.bar(
                    d, x="Cargo", y="Avaliação", title="Avaliação Média por Cargo",
                    color_discrete_sequence=["#b39ddb"],
                    template="plotly_dark"
                )
                fig.update_layout(
                    plot_bgcolor="#232336", paper_bgcolor="#232336",
                    font_color="#e0e0e0", title_font_color="#6c3fcf"
                )
                st.plotly_chart(fig, use_container_width=True)

st.divider()

# --------------------- Tabela e Downloads ---------------------
st.subheader("Tabela (dados filtrados)")
st.dataframe(filtered_df, use_container_width=True)

csv_bytes = filtered_df.to_csv(index=False).encode("utf-8")
st.download_button(
    "Baixar CSV filtrado",
    data=csv_bytes,
    file_name="funcionarios_filtrado.csv",
    mime="text/csv"
)

# Exportar Excel filtrado (opcional)
to_excel = st.toggle("Gerar Excel filtrado para download")
if to_excel:
    from io import BytesIO
    buff = BytesIO()
    with pd.ExcelWriter(buff, engine="openpyxl") as writer:
        filtered_df.to_excel(writer, index=False, sheet_name="Filtrado")
    st.download_button(
        "Baixar Excel filtrado",
        data=buff.getvalue(),
        file_name="funcionarios_filtrado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

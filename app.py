import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px

# ⬇️ PRIMEIRA LINHA Streamlit
st.set_page_config(page_title="Comparador de Saldos", layout="wide")

# ⬇️ DEPOIS do set_page_config
st.markdown("""
    <style>
        .stSelectbox, .stRadio { 
            color: #fafafa !important;
        }

        body {
            background-color: #0e1117;
            color: #fafafa;
        }
        .stApp {
            background-color: #0e1117;
        }
        .block-container {
            padding: 2rem 2rem;
        }
        h1, h2, h3, .stMarkdown {
            color: #fafafa !important;
        }
        .css-1d391kg, .css-1v3fvcr {
            background-color: #1c1f26 !important;
        }
    </style>
""", unsafe_allow_html=True)
 

# Conexão com banco
host = "localhost"
port = "5432"
user = "postgres"
password = "1234"
database = "precatorios"
engine = create_engine(f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}")

# Dados
df = pd.read_sql("SELECT * FROM movimentacoes", engine)
df['data_movimentacao'] = pd.to_datetime(df['data_movimentacao'], errors='coerce')

# Título
st.markdown("## 🔍 Movimentações")

# Filtro de município
municipios = sorted(df['municipio'].dropna().unique())
municipio_select = st.selectbox("🏙️ Selecione o Município", options=municipios)
df_mun = df[df['municipio'] == municipio_select]

# Converter para datetime.date
datas_unicas = df_mun['data_movimentacao'].dropna().dt.date.unique()
datas_ordenadas = sorted(datas_unicas)

# Criar dicionário para mapear data formatada -> data original
datas_formatadas = {data.strftime("%d/%m/%Y"): data for data in datas_ordenadas}

# Seletor de datas
col1, col2 = st.columns(2)
col1, col2 = st.columns(2)
with col1:
    data1_str = st.selectbox("📅 Data 1 - Saldo Anterior", options=list(datas_formatadas.keys()))
    data1 = datas_formatadas[data1_str]
with col2:
    data2_str = st.selectbox("📅 Data 2 - Saldo Atualizado", options=list(datas_formatadas.keys()), index=len(datas_formatadas) - 1)
    data2 = datas_formatadas[data2_str]
    
    
# Função para resumo por data_movimentacao e município
def resumo_por_data_municipio(df_base):
    grupos = df_base.groupby(['data_movimentacao', 'municipio'])
    resultado = []

    for (data, municipio), grupo in grupos:
        menor_id = grupo.loc[grupo['id'].idxmin()]
        maior_id = grupo.loc[grupo['id'].idxmax()]

        resultado.append({
            'Data da Movimentação': data.date(),
            'Município': municipio,
            'Saldo Anterior (menor ID)': menor_id['saldo_anterior_valor'],
            'Saldo Atualizado (maior ID)': maior_id['saldo_atualizado_valor'],
            'Diferença': maior_id['saldo_atualizado_valor'] - menor_id['saldo_anterior_valor']
        })
    df_resultado = pd.DataFrame(resultado)
    
    # Ordena corretamente por data
    df_resultado = df_resultado.sort_values(by='Data da Movimentação', ascending=False)
    
    # Só então formata como string
    df_resultado['Data da Movimentação'] = df_resultado['Data da Movimentação'].apply(lambda x: x.strftime('%d/%m/%Y'))

    return df_resultado
    
# Funções de saldo
def get_saldo_anterior(df_base, data):
    df_data = df_base[df_base['data_movimentacao'].dt.date == data]
    if df_data.empty:
        return None
    menor_id = df_data.loc[df_data['id'].idxmin()]
    return menor_id['saldo_anterior_valor']

def get_saldo_atualizado(df_base, data):
    df_data = df_base[df_base['data_movimentacao'].dt.date == data]
    if df_data.empty:
        return None
    maior_id = df_data.loc[df_data['id'].idxmax()]
    return maior_id['saldo_atualizado_valor']

# Calcular saldos
saldo_anterior = get_saldo_anterior(df_mun, data1)
saldo_atualizado = get_saldo_atualizado(df_mun, data2)

# Resultados
if saldo_anterior is not None and saldo_atualizado is not None:
    diferenca = saldo_atualizado - saldo_anterior

    st.markdown("---")
    st.markdown(f"### 📊 Resultados para **{municipio_select}**")

    # Cards
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Saldo Anterior", f"R$ {saldo_anterior:,.2f}")
    col2.metric("💼 Saldo Atualizado", f"R$ {saldo_atualizado:,.2f}")
    col3.metric("📈 Diferença", f"R$ {diferenca:,.2f}", delta=f"{'+' if diferenca > 0 else ''}{diferenca:,.2f}")


        # Tabela
    resultado = pd.DataFrame([{
        "Município": municipio_select,
        "Data 1 (Saldo Anterior)": data1,
        "Saldo Anterior": saldo_anterior,
        "Data 2 (Saldo Atualizado)": data2,
        "Saldo Atualizado": saldo_atualizado,
        "Diferença": diferenca
    }])
     
    
        # Seção: Visualização Geral por Data e Município
    st.markdown("---")
    st.header("📊 Visualização Geral das Movimentações")

    # Ordenar por data mais recente
    df_sorted = df.sort_values(by="data_movimentacao", ascending=False)

    df_grouped = (
    df_sorted.groupby(["data_movimentacao", "municipio"])
    .agg({
        "saldo_anterior_valor": "min",   # Início do dia
        "saldo_atualizado_valor": "max"  # Fim do dia
    })
    .reset_index()
)

    
    # Filtro adicional para gráfico/planilha geral
    st.markdown("### 🔎 Filtro por Município na Visualização Geral")
    
    municipios_disponiveis = sorted(df_grouped['municipio'].unique())
    municipio_filtro = st.selectbox("🔎 Filtrar município na visualização geral", options=["Todos"] + municipios_disponiveis)

    if municipio_filtro != "Todos":
        df_grouped = df_grouped[df_grouped['municipio'] == municipio_filtro]



    # Botão de alternância entre gráfico e planilha
    modo_visualizacao = st.radio("Modo de Visualização", options=["Planilha", "Gráfico"], horizontal=True)
    
    df_grouped["Movimentação"] = df_grouped["saldo_atualizado_valor"] - df_grouped["saldo_anterior_valor"]

    if modo_visualizacao == "Gráfico":
        fig_bar = px.bar(
            df_grouped.melt(
                id_vars=["data_movimentacao", "municipio"],
                value_vars=["saldo_anterior_valor", "saldo_atualizado_valor"],
                var_name="Tipo de Saldo",
                value_name="Valor"
            ),
            x="data_movimentacao",
            y="Valor",
            color="Tipo de Saldo",
            barmode="group",
            title="Saldos no Início e Fim do Dia",
            labels={
                "data_movimentacao": "Data",
                "Valor": "Valor (R$)",
                "Tipo de Saldo": "Tipo de Saldo"
            },
            template="plotly_dark"
        )

        st.plotly_chart(fig_bar, use_container_width=True)

    else:
        
        # Gerar e exibir resumo
        
        df_resumo = resumo_por_data_municipio(df)

        st.title("📋 Tabela de Resumo por Data e Município")
        st.dataframe(df_resumo, use_container_width=True)
 




else:
    st.warning("⚠️ Dados insuficientes para calcular os saldos nas datas selecionadas.")

 

# cade_dashboard.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from processamento import analisa
#from analise import 


st.sidebar.header("⚙️ Configuração de Leitura")

csv_path = "../dados/df_preparado.csv"

df_counter = pd.read_csv(csv_path, usecols=[0])
max_n = df_counter.shape[0]

# 2) Exibe para o usuário o total de registros disponíveis
st.sidebar.markdown(f"**Total de registros disponíveis:** {max_n}")

# inicializa em session_state se ainda não existir
if "nrows" not in st.session_state:
    st.session_state.nrows = 100  # valor padrão

# input para número de linhas
n_input = st.sidebar.number_input(
    "Linhas para carregar",
    min_value=1,
    value=st.session_state.nrows,
    step=1
)
# botão para confirmar
if st.sidebar.button("🔄 Carregar CSV"):
    st.session_state.nrows = n_input
    
# lê apenas as primeiras nrows linhas
df = pd.read_csv("../dados/df_preparado.csv", nrows=st.session_state.nrows)


sectors = df['setor_economico_secao'].drop_duplicates().tolist()
decisions = df['decisao_tribunal'].drop_duplicates().tolist()
gabinetes = df['sigla_unidade'].drop_duplicates().tolist()
#infr_types = ["Cartel", "Abuso de posição dominante", "Ato de Concentração", "Conduta Unilateral"]

# -------------------------------------------------------------------
# Sidebar – filtros
# -------------------------------------------------------------------

st.sidebar.header("⚖️ Filtros Jurídicos")

sector_sel = st.sidebar.multiselect("Setor econômico", options=sectors, default=sectors)
decision_sel = st.sidebar.multiselect("Tipo de decisão", options=decisions, default=decisions)
gabinetes = st.sidebar.multiselect("Gabinete", options=gabinetes, default=gabinetes)

date_min, date_max = st.sidebar.date_input(
    "Data do processo",
    value=(df["data_processo"].min(), df["data_processo"].max()),
    min_value=df["data_processo"].min(),
    max_value=df["data_processo"].max()
)

# Apply filters
mask = (
    df['setor_economico_secao'].isin(sector_sel)
    & df["decisao_tribunal"].isin(decision_sel)
    & df["sigla_unidade"].isin(gabinetes)
    & df["diferenca_dias"].between(int(df["diferenca_dias"].min()), int(df["diferenca_dias"].max()))
)

#if nota_opt != "Indiferente":
#    mask &= df["seguiu_nota_tecnica"] == (nota_opt == "Sim")

filtered_df = df[mask]

# -------------------------------------------------------------------
# 3. KPIs específicos
# -------------------------------------------------------------------
st.title("📊 Painel Jurídico Interativo")

col1, col2 = st.columns(2)
col1.metric("Casos filtrados", f"{len(filtered_df):,}")
conden = filtered_df["decisao_tribunal"].eq("condenacao").sum()
col2.metric("Taxa de condenação", f"{conden/len(filtered_df)*100 if len(filtered_df) else 0:.1f}%")
#nota_pct = filtered_df["seguiu_nota_tecnica"].mean() * 100 if len(filtered_df) else 0
#col3.metric("Seguiu Nota Técnica", f"{nota_pct:.1f}%")
#col4.metric("Multas totais (R$)", f"R$ {filtered_df['fine_value_reais'].sum():,.0f}")

st.divider()

# -------------------------------------------------------------------
# Análise de decisões por grupo economico
# -------------------------------------------------------------------

chart_df = filtered_df.copy()
chart_df['setor_economico_secao'] = chart_df['setor_economico_secao'].apply(
    lambda x: ' '.join(x.split()[:4]) + (' ...' if len(x.split()) > 4 else '')
)


st.subheader("Distribuição de decisões por grupo economico")
decisions_by_inf = (
    chart_df.groupby(['setor_economico_secao', "decisao_tribunal"])
    .size()
    .reset_index(name="count")
)

fig1 = px.bar(
    decisions_by_inf,
    x='setor_economico_secao',
    y="count",
    color="decisao_tribunal",
    barmode="group",
    labels={'setor_economico_secao': "grupo economico", "count": "Número de casos", "decisao_tribunal": "Decisão"}
)
st.plotly_chart(fig1, use_container_width=True)

chart_df['taxa_condenacao_gabinete'] = (chart_df['decisao_tribunal'] == 'condenacao').astype(int)
# Agrupe por gabinete e calcule a média (taxa de condenação)
taxa_condenacao = chart_df.groupby('setor_economico_secao')['taxa_condenacao_gabinete'].mean().reset_index()
taxa_condenacao.columns = ['setor_economico_secao', 'taxa_condenacao']

st.subheader("Taxa de Condenação por grupo econômico")
fig2 = px.bar(
    taxa_condenacao,
    x="taxa_condenacao",
    y="setor_economico_secao",
    orientation='h',
    text_auto=".1%",
    labels={
        "setor_economico_secao": "Setor econômico",
        "taxa_condenacao": "Taxa de Condenação"
    },
    color_discrete_sequence=["#1E5A92"]  # Verde para destaque positivo
)
st.plotly_chart(fig2, use_container_width=True)

# -------------------------------------------------------------------
# 4A. Análise por gabinete
# -------------------------------------------------------------------

#Distribuição de decisões por gabinete
st.subheader("Distribuição de decisões por gabinete")
decisions_by_inf = (
    filtered_df.groupby(["sigla_unidade", "decisao_tribunal"])
    .size()
    .reset_index(name="count")
)
fig1 = px.bar(
    decisions_by_inf,
    x="sigla_unidade",
    y="count",
    color="decisao_tribunal",
    barmode="group",
    labels={"sigla_unidade": "gabinete avaliador", "count": "Número de casos", "decisao_tribunal": "Decisão"}
)
st.plotly_chart(fig1, use_container_width=True)

#Taxa de condenação por gabinete

df['taxa_condenacao_gabinete'] = (df['decisao_tribunal'] == 'condenacao').astype(int)
# Agrupe por gabinete e calcule a média (taxa de condenação)
taxa_condenacao = df.groupby('sigla_unidade')['taxa_condenacao_gabinete'].mean().reset_index()
taxa_condenacao.columns = ['sigla_unidade', 'taxa_condenacao']

st.subheader("Taxa de Condenação por Gabinete")
fig2 = px.bar(
    taxa_condenacao,
    x="taxa_condenacao",
    y="sigla_unidade",
    orientation='h',
    text_auto=".1%",
    labels={
        "sigla_unidade": "Gabinete",
        "taxa_condenacao": "Taxa de Condenação"
    },
    color_discrete_sequence=["#1E5A92"]  # Verde para destaque positivo
)
st.plotly_chart(fig2, use_container_width=True)

#Distribuição proporcional da quantidade de processos por gabinete
st.subheader("Distribuição proporcional da quantidade de processos por gabinete")

# Agrupa e calcula porcentagens
processos_por_gabinete = filtered_df["sigla_unidade"].value_counts(normalize=True).reset_index()
processos_por_gabinete.columns = ["sigla_unidade", "percentual"]

fig3 = px.pie(
    processos_por_gabinete,
    names="sigla_unidade",
    values="percentual",
    labels={"sigla_unidade": "Gabinete Avaliador", "percentual": "Proporção"},
    hole=0.15  # Donut chart
)
fig3.update_traces(textposition='inside', textinfo='percent+label')
st.plotly_chart(fig3, use_container_width=True)

# -------------------------------------------------------------------
# 4C. Análise de dias do processo
# -------------------------------------------------------------------

st.subheader("Distribuição do prazo em relação a decisão do processo")
if filtered_df["diferenca_dias"].gt(0).any():
    fig3 = px.box(
        filtered_df[filtered_df["diferenca_dias"] > 0],
        x="decisao_tribunal", y="diferenca_dias",
        labels={"decisao_tribunal": "Decisão", "diferenca_dias": "Dias entre processo e documento"}
    )
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("Nenhuma multa nos dados filtrados.")

#Dias do processo por gabinete
st.subheader("Distribuição do prazo em relação ao gabinete")
if filtered_df["diferenca_dias"].gt(0).any():
    fig3 = px.box(
        filtered_df[filtered_df["diferenca_dias"] > 0],
        x="sigla_unidade", y="diferenca_dias",
        labels={"sigla_unidade": "Gabinete avaliador", "diferenca_dias": "Dias entre processo e documento"}
    )
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("Nenhuma multa nos dados filtrados.")

#Dias do processo por setor economico
st.subheader("Distribuição do prazo em relação ao setor economico")

fig3 = px.box(
    chart_df[chart_df["diferenca_dias"] > 0],
    x="setor_economico_secao", y="diferenca_dias",
    labels={"setor_economico_secao": "Setor economico", "diferenca_dias": "Dias entre processo e documento"}
)
st.plotly_chart(fig3, use_container_width=True)

# -------------------------------------------------------------------
# 5. Dados brutos
# -------------------------------------------------------------------
colunas_para_mostrar = ['id', 'numero_sei', 'ano_documento', 'assinaturas', 'descricao_tipo_documento',
                  'decisao_tribunal', 'setor_economico_secao', 'sigla_unidade', 'data_processo',
                     'data_documento', 'diferenca_dias', 'mercado_relevante','documentos_relacionados', 'descricao_especificacao', 'conteudo' ]

with st.expander("🔍 Ver dados brutos"):
    st.dataframe(filtered_df[colunas_para_mostrar].sort_values("data_processo").reset_index(drop=True))

    # Inicialização do Session State
if 'data_ready' not in st.session_state:
    st.session_state.data_ready = False
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None


def processar_dados():
    with st.spinner('Processando dados...'):
        df_ia = analisa(filtered_df)
        st.session_state.data_ready = True
        st.session_state.processed_data = df_ia
    return 

# Função para calcular tempo estimado e custo estimado
def calcular_estimativas(df):
    num_linhas = len(df)
    tempo_estimado = (num_linhas / 100) * 5  # minutos
    custo_estimado = num_linhas * 0.10  # R$ 0,10 por linha
    return num_linhas, tempo_estimado, custo_estimado

# Calcule as estimativas com o seu dataframe filtrado
num_linhas, tempo_estimado, custo_estimado = calcular_estimativas(filtered_df)


# Interface principal
st.title("📊 Análise baseada em IA")

# Crie as colunas: a primeira (infos) ocupa mais espaço, a última (botão) menos
col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

with col1:
    st.markdown(f"**Nº de linhas:** {num_linhas}")

with col2:
    st.markdown(f"**Tempo estimado:**<br>{tempo_estimado:.1f} min", unsafe_allow_html=True)

with col3:
    st.markdown(f"**Custo estimado:**<br>R$ {custo_estimado:.2f}", unsafe_allow_html=True)

with col4:
    st.write("") 
    if st.button("▶️ Gerar Gráficos", on_click=processar_dados, use_container_width=True):
        pass

    

# 2. Placeholders para os gráficos
grafico1_placeholder = st.empty()
grafico2_placeholder = st.empty()
grafico3_placeholder = st.empty()
grafico4_placeholder = st.empty()

# 3. Gráfico temporário (estrutura sem dados)
if not st.session_state.data_ready:
    with grafico1_placeholder:
        fig_temp = px.box(title="Valor da multa geral (R$) (aguardando dados...)")
        fig_temp.update_layout(xaxis_title="Data", yaxis_title="Valor")
        st.plotly_chart(fig_temp, use_container_width=True)
    
    with grafico2_placeholder:
        fig_temp = px.bar(title="Valor da multa por setor (aguardando dados...)")
        fig_temp.update_layout(xaxis_title="Setor", yaxis_title="Valor da multa")
        st.plotly_chart(fig_temp, use_container_width=True)

    with grafico3_placeholder:
        fig_temp = px.pie(title="Tipo de multa (aguardando dados...)")
        fig_temp.update_layout(xaxis_title="Categoria", yaxis_title="Contagem")
        st.plotly_chart(fig_temp, use_container_width=True)

    with grafico4_placeholder:
        fig_temp = px.bar(title="Tipo de infra;'ao (aguardando dados...)")
        fig_temp.update_layout(xaxis_title="Categoria", yaxis_title="Contagem")
        st.plotly_chart(fig_temp, use_container_width=True)

# 4. Gráficos reais quando os dados estiverem prontos
else:
    df = st.session_state.processed_data
    
    with grafico1_placeholder:
        if df is not None and not df.empty:
            st.subheader("Distribuição dos valores de multa no geral")
            fig1 = px.box(df,
                x="descricao_tipo_processo", y="valor_multa_reais_ia",
                labels={"descricao_tipo_processo": "Processos", "valor_multa_reais_ia": "Valor da Multa (R$)"}
            )
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.warning("Não há dados disponíveis para gerar o gráfico.")


    with grafico2_placeholder:
        if df is not None and not df.empty:
            st.subheader("Distribuição dos valores de multa por setor econômico")
            fig2 = px.box(df,
                x="setor_economico_secao", y="valor_multa_reais_ia",
                labels={"setor_economico_secao": "Setor econômico", "valor_multa_reais_ia": "Valor da Multa (R$)"}
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.warning("Não há dados disponíveis para gerar o gráfico.")


    with grafico3_placeholder:
        if df is not None and not df.empty:
            counts = df['tipo_de_multa_ia'].value_counts().reset_index()
            counts.columns = ['tipo_de_multa_ia', 'count']

            st.subheader("Distribuição dos valores de multa por setor econômico")
            fig3 = px.pie(counts,
                names="tipo_de_multa_ia", values="count",
                title="Proporção dos tipos de multa"
            )
            st.plotly_chart(fig3, use_container_width=True)
            fig3.update_traces(textinfo='percent+label')
        else:
            st.warning("Não há dados disponíveis para gerar o gráfico.")

    with grafico4_placeholder:
        if df is not None and not df.empty:
            counts = df['tipo_infracao_concorrencial_ia'].value_counts().reset_index()
            counts.columns = ['tipo_infracao_concorrencial_ia', 'count']

            st.subheader("Distribuição dos valores de multa por setor econômico")
            fig4 = px.bar(counts,
                x="tipo_infracao_concorrencial_ia", y="count",
                labels={"tipo_infracao_concorrencial_ia": "Tipo de infração", "count": "proporção"}
            )
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.warning("Não há dados disponíveis para gerar o gráfico.")
        
    

# 5. Seção para dados brutos (condicional)
if st.session_state.data_ready:
    with st.expander("📁 Visualizar Dados Processados"):
        st.dataframe(df, use_container_width=True)

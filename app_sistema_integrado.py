import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import base64
import os
import requests
import re
import hashlib
import hmac

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA WEB & FAVICON
# ==============================================================================
diretorio_atual = os.path.dirname(os.path.abspath(__file__))
candidatos_logo = ["logo.png", "logo.jpg", "logo.jpeg", "LOGO.PNG", "LOGO.JPG"]
caminho_logo_encontrado = None

for nome_img in candidatos_logo:
    caminho_completo = os.path.join(diretorio_atual, nome_img)
    if os.path.exists(caminho_completo):
        caminho_logo_encontrado = caminho_completo
        break

st.set_page_config(
    page_title="Micro Fox Soluções em TI - Sistema Integrado de Gestão", 
    page_icon=caminho_logo_encontrado if caminho_logo_encontrado else "🛠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 2. AUTENTICAÇÃO E SEGURANÇA (ST.SECRETS + SHA-256 + FALLBACK SEGURO)
# ==============================================================================
# Tenta obter as credenciais do Secrets, caso contrário ativa o Fallback padrão seguro
try:
    USUARIO_CORRETO = str(st.secrets["auth"]["username"]).strip().lower()
    if "password" in st.secrets["auth"]:
        SENHA_CORRETA = str(st.secrets["auth"]["password"]).strip()
        MODO_AUTENTICACAO = "direta"
    else:
        HASH_SENHA_CORRETA = str(st.secrets["auth"]["password_hash"]).strip().lower()
        MODO_AUTENTICACAO = "hash"
except Exception:
    USUARIO_CORRETO = "admin"
    SENHA_CORRETA = "MFoxinfo@123"
    MODO_AUTENTICACAO = "direta"

def validar_credenciais(usuario_digitado, senha_digitada):
    """Valida o usuário e a senha protegendo contra timing attacks."""
    if not usuario_digitado or not senha_digitada:
        return False
    
    usuario_valido = hmac.compare_digest(usuario_digitado.strip().lower(), USUARIO_CORRETO)
    
    if MODO_AUTENTICACAO == "direta":
        senha_valida = hmac.compare_digest(senha_digitada.strip(), SENHA_CORRETA)
    else:
        hash_digitado = hashlib.sha256(senha_digitada.strip().encode('utf-8')).hexdigest().lower()
        senha_valida = hmac.compare_digest(hash_digitado, HASH_SENHA_CORRETA)
        
    return usuario_valido and senha_valida

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

# ==============================================================================
# 3. TRATAMENTO HTML E EMBED DA LOGO
# ==============================================================================
logo_html, logo_banner_html, watermark_html = "", "", ""

if caminho_logo_encontrado:
    with open(caminho_logo_encontrado, "rb") as image_file:
        logo_b64 = base64.b64encode(image_file.read()).decode()
        src_data = f"data:image/png;base64,{logo_b64}"
        
        logo_html = f'<img src="{src_data}" style="max-height: 65px; max-width: 160px; margin-right: 15px;"/>'
        logo_banner_html = (
            f'<img src="{src_data}" '
            'style="width: 90px; height: 90px; border-radius: 50%; object-fit: cover; border: 2px solid #38bdf8; margin-bottom: 5px;"/>'
        )
        watermark_html = f'<img src="{src_data}" class="watermark"/>'

# --- TEXTOS PADRÃO ---
TEXTO_GARANTIA_ORCAMENTO = """GARANTIA DE EQUIPAMENTOS E SERVIÇOS
Forneceremos 01 (um) ano de garantia dos produtos e 03 (três) meses de garantia dos nossos serviços e consultoria gratuita pelo mesmo período.
Nos preços cotados não estão incluídos serviços de desobstrução e/ou substituição de tubulação que eventualmente se façam necessários, bem como obras civis associadas.
Qualquer outro tipo de serviço que seja necessário será informado com antecedência para que seja tomada as providencias cabíveis, será cobrado a taxa de 250,00 adicional."""

# --- ESTILIZAÇÃO CSS CUSTOMIZADA ---
st.markdown("""
<style>
    .stApp { background-color: #0f172a !important; color: #f8fafc !important; }
    [data-testid="stSidebar"] { background-color: #020617 !important; border-right: 1px solid #1e293b; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: #38bdf8 !important; font-weight: 700; }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] span, [data-testid="stSidebar"] p { color: #cbd5e1 !important; font-weight: 600; }
    [data-testid="stSidebar"] input { color: #0f172a !important; background-color: #ffffff !important; border-radius: 6px !important; }
    h1, h2, h3 { color: #38bdf8 !important; font-family: 'Inter', Arial, sans-serif; font-weight: 700; }
    .stMainBlockContainer label, .stMainBlockContainer p, .stMainBlockContainer caption { color: #cbd5e1 !important; font-weight: 600 !important; }
    .stMainBlockContainer input, .stMainBlockContainer textarea, .stMainBlockContainer select, div[data-baseweb="select"] span {
        color: #0f172a !important; background-color: #ffffff !important; font-weight: 500 !important;
    }
    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
        border-radius: 8px !important; border: 1px solid #334155 !important; background-color: #ffffff !important;
    }
    .metric-card {
        background-color: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2); text-align: center;
    }
    .metric-title { font-size: 13px; color: #94a3b8 !important; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .metric-value { font-size: 24px; color: #38bdf8 !important; font-weight: 700; margin-top: 5px; }
    .stButton > button {
        background-color: #2563eb !important; color: #ffffff !important; font-weight: 700 !important;
        border-radius: 8px !important; padding: 10px 24px !important; border: none !important; text-transform: uppercase; font-size: 12px; letter-spacing: 0.5px;
    }
    .stButton > button:hover { background-color: #3b82f6 !important; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4); }
    .section-card { background-color: #1e293b; border-radius: 12px; padding: 24px; border: 1px solid #334155; margin-bottom: 20px; }
    
    .hero-banner {
        background: linear-gradient(135deg, #020617 0%, #1e293b 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 25px 30px;
        margin-bottom: 25px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
    }
    .hero-title { font-size: 26px; font-weight: 700; color: #38bdf8; margin-top: 10px; text-transform: uppercase; letter-spacing: 1px; }
    .hero-subtitle { font-size: 14px; color: #94a3b8; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÃO CONSULTA CNPJ VIA BRASILAPI ---
def consultar_cnpj_api(cnpj):
    cnpj_limpo = re.sub(r'\D', '', cnpj)
    if len(cnpj_limpo) == 14:
        try:
            url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                dados = res.json()
                return {
                    "nome": dados.get("razao_social") or dados.get("nome_fantasia"),
                    "endereco": f"{dados.get('descricao_tipo_de_logradouro', '')} {dados.get('logradouro', '')}, {dados.get('numero', '')} {dados.get('complemento', '')}".strip(),
                    "bairro": dados.get("bairro", ""),
                    "cidade": (dados.get("municipio") or "BRASÍLIA").upper(),
                    "uf": (dados.get("uf") or "DF").upper(),
                    "telefone": dados.get("ddd_telefone_1", "")
                }
        except Exception:
            pass
    return None

LISTA_UFS = ["DF", "AC", "AL", "AM", "AP", "BA", "CE", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"]

@st.cache_data(ttl=86400)
def buscar_cidades_por_uf(sigla_uf):
    try:
        url = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{sigla_uf}/municipios?orderBy=nome"
        res = requests.get(url, timeout=5).json()
        return [c["nome"] for c in res]
    except Exception:
        if sigla_uf == "DF":
            return ["BRASÍLIA", "SAMAMBAIA", "TAGUATINGA", "CEILÂNDIA", "ÁGUAS CLARAS", "GAMA", "SOBRADINHO"]
        return ["Capital / Centro"]

# ==============================================================================
# TELA DE AUTENTICAÇÃO / LOGIN
# ==============================================================================
if not st.session_state["autenticado"]:
    col_l1, col_l2, col_l3 = st.columns([1, 1.5, 1])
    with col_l2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        card_html = (
            '<div style="text-align: center; background-color: #1e293b; padding: 30px; border-radius: 12px; border: 1px solid #334155;">'
            f'{logo_banner_html}'
            '<h2 style="color: #38bdf8; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px;">MICRO FOX TI</h2>'
            '<p style="color: #94a3b8; font-size: 13px; margin-bottom: 0;">SISTEMA CORPORATIVO DE O.S. E ORÇAMENTOS</p>'
            '</div>'
        )

        st.markdown(card_html, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        with st.form("form_login"):
            usuario = st.text_input("Usuário de Acesso", placeholder="Ex: admin")
            senha = st.text_input("Senha", type="password", placeholder="••••••••")
            btn_entrar = st.form_submit_button("🔒 ACESSAR O SISTEMA", use_container_width=True)
            
            if btn_entrar:
                if validar_credenciais(usuario, senha):
                    st.session_state["autenticado"] = True
                    st.success("Autenticado com sucesso.")
                    st.rerun()
                else:
                    st.error("⚠️ Usuário ou senha incorretos.")
    st.stop()

# ==============================================================================
# BANCO DE DADOS UNIFICADO (SQLITE)
# ==============================================================================
conn = sqlite3.connect("sistema_os.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("PRAGMA foreign_keys = ON;")

cursor.executescript("""
CREATE TABLE IF NOT EXISTS clientes (
    id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    cpf_cnpj TEXT,
    telefone TEXT,
    contato TEXT,
    endereco TEXT,
    bairro TEXT,
    cidade TEXT,
    uf TEXT,
    cep TEXT
);

CREATE TABLE IF NOT EXISTS ordens_servico (
    id_os INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_os TEXT,
    data_abertura TEXT,
    hora_abertura TEXT,
    cliente_id INTEGER,
    cliente_nome TEXT,
    cliente_endereco TEXT,
    cliente_cpf_cnpj TEXT,
    cliente_contato TEXT,
    cliente_tel TEXT,
    cliente_bairro TEXT,
    cliente_cidade TEXT,
    cliente_uf TEXT,
    cliente_cep TEXT,
    equipamento TEXT,
    modelo TEXT,
    marca TEXT,
    acessorios TEXT,
    numero_serie TEXT,
    problema_informado TEXT,
    problema_constatado TEXT,
    servico_executado TEXT,
    garantia_texto TEXT,
    responsavel TEXT,
    situacao TEXT,
    data_saida TEXT,
    hora_saida TEXT,
    forma_pagamento TEXT,
    condicoes TEXT,
    val_produtos REAL DEFAULT 0.0,
    val_servicos REAL DEFAULT 0.0,
    val_deslocamento REAL DEFAULT 0.0,
    val_desconto REAL DEFAULT 0.0,
    val_total REAL DEFAULT 0.0,
    tipo_documento TEXT DEFAULT 'Comprovante de Saída',
    FOREIGN KEY(cliente_id) REFERENCES clientes(id_cliente)
);

CREATE TABLE IF NOT EXISTS itens_catalogo (
    id_item INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL,
    descricao TEXT NOT NULL,
    preco_venda REAL DEFAULT 0.0,
    estoque_qtd REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS orcamentos (
    id_orcamento INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_orcamento TEXT,
    data_emissao TEXT,
    data_validade TEXT,
    cliente_id INTEGER,
    cliente_nome TEXT,
    cliente_cpf_cnpj TEXT,
    cliente_tel TEXT,
    cliente_email TEXT,
    cliente_cidade TEXT,
    equipamento TEXT,
    observacoes TEXT,
    condicoes_pagamento TEXT,
    prazo_entrega TEXT,
    val_subtotal REAL DEFAULT 0.0,
    val_desconto REAL DEFAULT 0.0,
    val_total REAL DEFAULT 0.0,
    status TEXT DEFAULT 'Pendente'
);

CREATE TABLE IF NOT EXISTS orcamento_itens (
    id_item INTEGER PRIMARY KEY AUTOINCREMENT,
    orcamento_id INTEGER,
    tipo TEXT,
    descricao TEXT,
    qtd REAL DEFAULT 1,
    val_unitario REAL DEFAULT 0.0,
    val_total_item REAL DEFAULT 0.0,
    FOREIGN KEY(orcamento_id) REFERENCES orcamentos(id_orcamento) ON DELETE CASCADE
);
""")
conn.commit()

# ==============================================================================
# BARRA LATERAL DA EMPRESA E MENU INTEGRADO
# ==============================================================================
st.sidebar.markdown("### Dados da Empresa")
empresa_nome = st.sidebar.text_input("Razão Social", "MICRO FOX SOLUÇÕES E SERVIÇOS EM TI")
empresa_end = st.sidebar.text_input("Endereço/Cidade", "QN 312 CJ 4 LT 2 SAMAMBAIA - SUL - BRASÍLIA-DF")
empresa_cnpj = st.sidebar.text_input("CNPJ", "18.710.097/0001-91")
empresa_tel = st.sidebar.text_input("Telefone", "(61) 3246-6001")
empresa_email = st.sidebar.text_input("E-mail", "atendimento@microfox.com.br")

st.sidebar.markdown("---")
st.sidebar.markdown("### Navegação Geral")

opcoes_menu = [
    "Painel de Controle (Dashboard)",
    "Criar Ordem de Serviço (O.S.)",
    "Consultar / Imprimir O.S.",
    "Criar Orçamento Comercial",
    "Consultar / Imprimir Orçamento",
    "Base de Clientes",
    "Catálogo de Produtos e Serviços"
]

if "menu_principal_nav" not in st.session_state:
    st.session_state["menu_principal_nav"] = "Painel de Controle (Dashboard)"

menu_principal = st.sidebar.radio(
    "Selecione o Módulo", 
    opcoes_menu, 
    index=opcoes_menu.index(st.session_state["menu_principal_nav"]),
    key="menu_radio_key"
)

st.session_state["menu_principal_nav"] = menu_principal

st.sidebar.markdown("---")
if st.sidebar.button("Encerrar Sessão", use_container_width=True):
    st.session_state["autenticado"] = False
    st.rerun()

# --- BANNER SUPERIOR CENTRALIZADO ---
banner_centralizado_html = (
    '<div class="hero-banner">'
    f'{logo_banner_html}'
    '<div class="hero-title">MICRO FOX SOLUÇÕES EM TI</div>'
    '<div class="hero-subtitle">Sistema Integrado de Ordens de Serviço e Propostas Comerciais</div>'
    '</div>'
)
st.markdown(banner_centralizado_html, unsafe_allow_html=True)

# ==============================================================================
# MÓDULOS DO SISTEMA
# ==============================================================================

# --- DASHBOARD ---
if menu_principal == "Painel de Controle (Dashboard)":
    st.caption("Indicadores gerais e atalhos rápidos de navegação")

    tot_os = cursor.execute("SELECT COUNT(*) FROM ordens_servico").fetchone()[0]
    fat_os = cursor.execute("SELECT SUM(val_total) FROM ordens_servico").fetchone()[0] or 0.0
    tot_orc = cursor.execute("SELECT COUNT(*) FROM orcamentos").fetchone()[0]
    fat_orc = cursor.execute("SELECT SUM(val_total) FROM orcamentos WHERE status = 'Aprovado'").fetchone()[0] or 0.0

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)

    with col_m1:
        st.markdown(f'<div class="metric-title" style="text-align: center; margin-bottom: 5px;">Total de O.S.</div>', unsafe_allow_html=True)
        if st.button(f"📋 {tot_os} O.S.", key="btn_dash_tot_os", use_container_width=True):
            st.session_state["menu_principal_nav"] = "Consultar / Imprimir O.S."
            st.rerun()

    with col_m2:
        st.markdown(f'<div class="metric-title" style="text-align: center; margin-bottom: 5px;">Faturamento O.S.</div>', unsafe_allow_html=True)
        if st.button(f"💰 R$ {float(fat_os):,.2f}", key="btn_dash_fat_os", use_container_width=True):
            st.session_state["menu_principal_nav"] = "Consultar / Imprimir O.S."
            st.rerun()

    with col_m3:
        st.markdown(f'<div class="metric-title" style="text-align: center; margin-bottom: 5px;">Total Orçamentos</div>', unsafe_allow_html=True)
        if st.button(f"📄 {tot_orc} Propostas", key="btn_dash_tot_orc", use_container_width=True):
            st.session_state["menu_principal_nav"] = "Consultar / Imprimir Orçamento"
            st.rerun()

    with col_m4:
        st.markdown(f'<div class="metric-title" style="text-align: center; margin-bottom: 5px;">Aprovados</div>', unsafe_allow_html=True)
        if st.button(f"✅ R$ {float(fat_orc):,.2f}", key="btn_dash_fat_orc", use_container_width=True):
            st.session_state["menu_principal_nav"] = "Consultar / Imprimir Orçamento"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        st.subheader("Últimas Ordens de Serviço")
        df_ultimas_os = pd.read_sql_query("""
            SELECT numero_os AS 'Nº OS', cliente_nome AS 'Cliente', equipamento AS 'Equipamento', val_total AS 'Total (R$)'
            FROM ordens_servico ORDER BY id_os DESC LIMIT 5
        """, conn)
        st.dataframe(df_ultimas_os, use_container_width=True)
        
    with col_t2:
        st.subheader("Últimos Orçamentos")
        df_ultimos_orc = pd.read_sql_query("""
            SELECT numero_orcamento AS 'Nº Proposta', cliente_nome AS 'Cliente', val_total AS 'Total (R$)', status AS 'Status'
            FROM orcamentos ORDER BY id_orcamento DESC LIMIT 5
        """, conn)
        st.dataframe(df_ultimos_orc, use_container_width=True)

# --- CRIAR O.S. ---
elif menu_principal == "Criar Ordem de Serviço (O.S.)":
    st.caption("Cadastre novas ordens de serviço de Entrada ou Saída")

    if "cli_data" not in st.session_state:
        st.session_state["cli_data"] = {
            "id": None, "nome": "", "cpf_cnpj": "", "tel": "", 
            "contato": "", "end": "", "bairro": "", "cidade": "BRASÍLIA", "uf": "DF"
        }

    cursor.execute("SELECT id_cliente, nome, cpf_cnpj, telefone, contato, endereco, bairro, cidade, uf FROM clientes ORDER BY nome ASC")
    lista_clientes = cursor.fetchall()
    opcoes_clientes = ["-- Novo Cliente / Preenchimento Manual --"] + [f"{c[1]} | {c[2] or 'Sem CPF/CNPJ'}" for c in lista_clientes]

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    cliente_selecionado = st.selectbox("Selecionar Cliente Cadastrado:", opcoes_clientes)
    
    if cliente_selecionado != "-- Novo Cliente / Preenchimento Manual --":
        idx = opcoes_clientes.index(cliente_selecionado) - 1
        cli_dados = lista_clientes[idx]
        st.session_state["cli_data"] = {
            "id": cli_dados[0], "nome": cli_dados[1] or "", "cpf_cnpj": cli_dados[2] or "",
            "tel": cli_dados[3] or "", "contato": cli_dados[4] or "", "end": cli_dados[5] or "",
            "bairro": cli_dados[6] or "", "cidade": (cli_dados[7] or "BRASÍLIA").upper(), "uf": (cli_dados[8] or "DF").upper()
        }

    st.markdown("---")
    col_b1, col_b2, col_b3 = st.columns([2, 1, 1])
    doc_digitado = col_b1.text_input("Buscar por CPF / CNPJ:", value=st.session_state["cli_data"]["cpf_cnpj"])
    
    if col_b2.button("Buscar CPF/CNPJ"):
        doc_limpo = re.sub(r'\D', '', doc_digitado)
        if doc_limpo:
            cursor.execute("""
                SELECT id_cliente, nome, cpf_cnpj, telefone, contato, endereco, bairro, cidade, uf 
                FROM clientes 
                WHERE REPLACE(REPLACE(REPLACE(REPLACE(cpf_cnpj, '.', ''), '-', ''), '/', ''), ' ', '') = ?
            """, (doc_limpo,))
            cli_local = cursor.fetchone()
            
            if cli_local:
                st.session_state["cli_data"] = {
                    "id": cli_local[0], "nome": cli_local[1], "cpf_cnpj": cli_local[2],
                    "tel": cli_local[3] or "", "contato": cli_local[4] or "", "end": cli_local[5] or "",
                    "bairro": cli_local[6] or "", "cidade": (cli_local[7] or "BRASÍLIA").upper(), "uf": (cli_local[8] or "DF").upper()
                }
                st.success(f"Cliente encontrado: {cli_local[1]}")
            else:
                if len(doc_limpo) == 14:
                    dados_api = consultar_cnpj_api(doc_limpo)
                    if dados_api:
                        st.session_state["cli_data"] = {
                            "id": None, "nome": dados_api["nome"], "cpf_cnpj": doc_digitado,
                            "tel": dados_api["telefone"], "contato": "", "end": dados_api["endereco"],
                            "bairro": dados_api["bairro"], "cidade": dados_api["cidade"], "uf": dados_api["uf"]
                        }
                        st.info("CNPJ localizado na Receita Federal.")
                    else:
                        st.warning("CNPJ não localizado na consulta pública.")
                else:
                    st.warning("CPF não localizado na base de dados.")
                    
    if col_b3.button("Limpar Dados"):
        st.session_state["cli_data"] = {"id": None, "nome": "", "cpf_cnpj": "", "tel": "", "contato": "", "end": "", "bairro": "", "cidade": "BRASÍLIA", "uf": "DF"}
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
    c_data = st.session_state["cli_data"]

    col_loc1, col_loc2 = st.columns([1, 3])
    uf_index = LISTA_UFS.index(c_data["uf"]) if c_data["uf"] in LISTA_UFS else 0
    uf_selecionada = col_loc1.selectbox("UF do Cliente *", LISTA_UFS, index=uf_index)
    
    lista_cidades_uf = buscar_cidades_por_uf(uf_selecionada)
    cidade_index = lista_cidades_uf.index(c_data["cidade"]) if c_data["cidade"] in lista_cidades_uf else 0
    cidade_selecionada = col_loc2.selectbox("Cidade do Cliente *", lista_cidades_uf, index=cidade_index)

    with st.form("form_os_completa"):
        st.subheader("1. Identificação da Ordem de Serviço")
        c1, c2, c3, c4 = st.columns(4)
        num_os_sugerido = datetime.now().strftime("%Y%m%d%H%M")
        numero_os = c1.text_input("Número da O.S. *", num_os_sugerido)
        data_abert = c2.date_input("Data de Abertura").strftime("%d/%m/%Y")
        hora_abert = c3.time_input("Hora de Abertura").strftime("%H:%M")
        tipo_doc_sel = c4.selectbox("Tipo de Comprovante *", ["Comprovante de Entrada", "Comprovante de Saída"])

        st.markdown("---")
        st.subheader("2. Dados do Cliente")
        col_c1, col_c2 = st.columns(2)
        cliente_nome = col_c1.text_input("Nome / Razão Social *", value=c_data["nome"])
        cliente_cpf = col_c2.text_input("CPF ou CNPJ", value=c_data["cpf_cnpj"] or doc_digitado)

        col_end1, col_end2 = st.columns([2, 1])
        cliente_end = col_end1.text_input("Endereço Completo", value=c_data["end"])
        cliente_bairro = col_end2.text_input("Bairro", value=c_data["bairro"])

        col_tel1, col_tel2 = st.columns(2)
        cliente_contato = col_tel1.text_input("Pessoa de Contato", value=c_data["contato"])
        cliente_tel = col_tel2.text_input("Telefone / WhatsApp", value=c_data["tel"])

        st.markdown("---")
        st.subheader("3. Especificações do Equipamento")
        col_eq1, col_eq2, col_eq3 = st.columns(3)
        equipamento = col_eq1.text_input("Equipamento", "")
        modelo = col_eq2.text_input("Modelo", "")
        marca = col_eq3.text_input("Marca", "")

        col_eq4, col_eq5 = st.columns(2)
        acessorios = col_eq4.text_input("Acessórios Deixados", "")
        num_serie = col_eq5.text_input("Nº de Série / Patrimônio", "")

        st.markdown("---")
        st.subheader("4. Diagnóstico Técnico e Laudo")
        prob_informado = st.text_area("Problema Informado pelo Cliente", "")
        prob_constatado = st.text_area("Problema Constatado na Bancada", "")
        servico_executado = st.text_area("Serviços Prestados e Peças Aplicadas", "")
        garantia_texto = st.text_input("Termos de Garantia (Apenas para Saída)", "90 DIAS PARA SERVIÇOS PRESTADOS")

        st.markdown("---")
        st.subheader("5. Fechamento e Valores")
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        responsavel = col_f1.text_input("Técnico Responsável", "Nelson Júnior")
        situacao = col_f2.text_input("Situação", "Na bancada" if tipo_doc_sel == "Comprovante de Entrada" else "Entrega direto para o cliente")
        forma_pag = col_f3.text_input("Forma de Pagamento", "PIX / Cartão")
        condicoes = col_f4.text_input("Condições", "À VISTA")

        col_v1, col_v2, col_v3, col_v4 = st.columns(4)
        v_prod = col_v1.number_input("Valor Produtos (R$)", value=0.0, step=10.0)
        v_serv = col_v2.number_input("Valor Serviços (R$)", value=0.0, step=10.0)
        v_desl = col_v3.number_input("Deslocamento (R$)", value=0.0, step=10.0)
        v_desc = col_v4.number_input("Desconto (R$)", value=0.0, step=10.0)

        v_tot_calculado = max(0.0, (v_prod + v_serv + v_desl) - v_desc)
        st.success(f"VALOR TOTAL CALCULADO: R$ {v_tot_calculado:.2f}")

        sub = st.form_submit_button("SALVAR E GERAR ORDEM DE SERVIÇO")

        if sub:
            if not cliente_nome or not numero_os:
                st.error("Preencha ao menos o Nome do Cliente e o Número da O.S.")
            else:
                cidade_formatada = f"{cidade_selecionada} / {uf_selecionada}"
                id_cli_existente = c_data["id"]
                
                if id_cli_existente:
                    cursor.execute("""
                        UPDATE clientes SET nome=?, cpf_cnpj=?, telefone=?, contato=?, endereco=?, bairro=?, cidade=?, uf=?
                        WHERE id_cliente=?
                    """, (cliente_nome, cliente_cpf, cliente_tel, cliente_contato, cliente_end, cliente_bairro, cidade_selecionada, uf_selecionada, id_cli_existente))
                    id_cli = id_cli_existente
                else:
                    cursor.execute("""
                        INSERT INTO clientes (nome, cpf_cnpj, telefone, contato, endereco, bairro, cidade, uf)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (cliente_nome, cliente_cpf, cliente_tel, cliente_contato, cliente_end, cliente_bairro, cidade_selecionada, uf_selecionada))
                    id_cli = cursor.lastrowid

                data_saida = datetime.now().strftime("%d/%m/%Y")
                hora_saida = datetime.now().strftime("%H:%M")

                cursor.execute("""
                    INSERT INTO ordens_servico (
                        numero_os, data_abertura, hora_abertura, cliente_id, cliente_nome, cliente_endereco, cliente_cpf_cnpj,
                        cliente_contato, cliente_tel, cliente_bairro, cliente_cidade, cliente_uf, equipamento, modelo, marca,
                        acessorios, numero_serie, problema_informado, problema_constatado, servico_executado,
                        garantia_texto, responsavel, situacao, data_saida, hora_saida, forma_pagamento, condicoes,
                        val_produtos, val_servicos, val_deslocamento, val_desconto, val_total, tipo_documento
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    numero_os, data_abert, hora_abert, id_cli, cliente_nome, cliente_end, cliente_cpf,
                    cliente_contato, cliente_tel, cliente_bairro, cidade_formatada, uf_selecionada, equipamento, modelo, marca,
                    acessorios, num_serie, prob_informado, prob_constatado, servico_executado,
                    garantia_texto, responsavel, situacao, data_saida, hora_saida, forma_pag, condicoes,
                    v_prod, v_serv, v_desl, v_desc, v_tot_calculado, tipo_doc_sel
                ))
                conn.commit()
                st.session_state["cli_data"] = {"id": None, "nome": "", "cpf_cnpj": "", "tel": "", "contato": "", "end": "", "bairro": "", "cidade": "BRASÍLIA", "uf": "DF"}
                st.success(f"Ordem de Serviço ({tipo_doc_sel}) Nº {numero_os} registrada com sucesso.")

# --- CONSULTAR O.S. ---
elif menu_principal == "Consultar / Imprimir O.S.":
    st.caption("Consulte e imprima os comprovantes de Entrada ou Saída de O.S.")
    
    df = pd.read_sql_query("SELECT id_os AS 'ID', numero_os AS 'Nº OS', cliente_nome AS 'Cliente', data_abertura AS 'Abertura', val_total AS 'Total (R$)', COALESCE(tipo_documento, 'Comprovante de Saída') AS 'Tipo' FROM ordens_servico ORDER BY id_os DESC", conn)
    st.dataframe(df, use_container_width=True)
    
    col_search1, col_search2 = st.columns([2, 1])
    id_sel = col_search1.number_input("Digite o ID da O.S. desejada:", min_value=1, step=1)
    
    if col_search2.button("Visualizar O.S."):
        cursor.execute("SELECT * FROM ordens_servico WHERE id_os = ?", (id_sel,))
        d = cursor.fetchone()
        
        if d:
            tipo_doc = d[34] if len(d) > 34 and d[34] else "Comprovante de Saída"
            
            if tipo_doc == "Comprovante de Entrada":
                def gerar_via_entrada(identificador_via):
                    return f"""
                    <div class="os-box">
                        {watermark_html}
                        <div class="os-header">
                            <div style="display: flex; align-items: center;">
                                {logo_html}
                                <div>
                                    <strong style="font-size: 13px;">{empresa_nome}</strong><br>
                                    <small style="font-size: 9px;">{empresa_end}</small><br>
                                    <small style="font-size: 9px;">{empresa_email}</small>
                                </div>
                            </div>
                            <div style="text-align: right; font-size: 10px;">
                                <strong>{empresa_tel}</strong><br>
                                <strong>CNPJ {empresa_cnpj}</strong>
                            </div>
                        </div>

                        <div class="os-title">COMPROVANTE DE ENTRADA - OS Nº {d[1]} &nbsp;&nbsp;&nbsp;&nbsp; Hora: {d[3]} &nbsp;&nbsp; Data: {d[2]}</div>

                        <div style="border: 1px solid #000; padding: 4px; margin: 4px 0; position: relative; z-index: 1;">
                            <strong>Cliente:</strong> {d[5]} &nbsp;&nbsp;&nbsp;&nbsp; <strong>Contato:</strong> {d[8]} &nbsp;&nbsp;&nbsp;&nbsp; <strong>Tel:</strong> {d[9]}<br>
                            <strong>Endereço:</strong> {d[6]}<br>
                            <strong>CPF/CNPJ:</strong> {d[7]} &nbsp;&nbsp; <strong>Bairro:</strong> {d[10]} &nbsp;&nbsp; <strong>Cidade:</strong> {d[11]}
                        </div>

                        <div class="os-section">
                            <div class="os-grid-3">
                                <div><strong>Equipamento:</strong> {d[14]}</div>
                                <div><strong>Modelo:</strong> {d[15]}</div>
                                <div><strong>Marca:</strong> {d[16]}</div>
                            </div>
                            <div class="os-grid-2" style="margin-top: 2px;">
                                <div><strong>Acessórios:</strong> {d[17]}</div>
                                <div><strong>Série/Tag:</strong> {d[18]}</div>
                            </div>
                        </div>

                        <div class="os-section">
                            <strong>Problema Informado:</strong> <span>{d[19] or 'Verificar equipamento.'}</span>
                        </div>

                        <div class="os-section">
                            <strong style="font-size: 10px;">CONDIÇÕES DE SERVIÇOS:</strong>
                            <div class="condic-list">
                                1) Aparelho só será devolvido mediante apresentação deste comprovante ou RG do titular; 
                                2) Se retirado por terceiros, avisar via WhatsApp/SMS no número acima; 
                                3) Taxa de R$ 60,00 para orçamento não autorizado; 
                                4) Autorizada abertura do equipamento para testes/troca de peças; 
                                5) Se não retirado em até 30 dias, a empresa poderá vendê-lo para cobrir custos; 
                                6) Backup mantido por 24h úteis após a retirada.
                            </div>
                        </div>

                        <div class="os-grid-2" style="margin-top: 4px;">
                            <div>
                                <strong>Data Entrada:</strong> {d[2]} &nbsp;&nbsp; <strong>Hora:</strong> {d[3]}<br>
                                <strong>Situação:</strong> {d[24]} &nbsp;&nbsp; <strong>Técnico:</strong> {d[23]}
                            </div>
                            <div style="text-align: right;">
                                <strong>Visto:</strong> {empresa_nome}
                            </div>
                        </div>

                        <div class="os-grid-2" style="margin-top: 15px;">
                            <div style="width: 45%;" class="signature-line">{identificador_via}</div>
                            <div style="width: 45%;" class="signature-line">Assinatura do Cliente</div>
                        </div>
                    </div>
                    """

                html_documento = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <style>
                        @page {{ size: A4 portrait; margin: 5mm 8mm; }}
                        body {{ font-family: Arial, Helvetica, sans-serif; font-size: 9px; color: #000; background-color: #fff; margin: 0; padding: 0; line-height: 1.2; }}
                        .page-container {{ width: 100%; box-sizing: border-box; }}
                        .os-box {{ border: 1px solid #000; padding: 8px 12px; background: #fff; position: relative; overflow: hidden; box-sizing: border-box; }}
                        .watermark {{
                            position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
                            opacity: 0.06; pointer-events: none; z-index: 0; width: 50%; max-width: 300px;
                        }}
                        .os-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1.5px solid #000; padding-bottom: 4px; margin-bottom: 4px; position: relative; z-index: 1; }}
                        .os-title {{ text-align: center; font-weight: bold; font-size: 11px; margin: 4px 0; border-top: 1px solid #000; border-bottom: 1px solid #000; padding: 2px 0; position: relative; z-index: 1; }}
                        .os-section {{ border-bottom: 1px dashed #777; padding: 3px 0; position: relative; z-index: 1; }}
                        .os-grid-2 {{ display: flex; justify-content: space-between; position: relative; z-index: 1; }}
                        .os-grid-3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; position: relative; z-index: 1; }}
                        .signature-line {{ border-top: 1px solid #000; margin-top: 18px; text-align: center; font-size: 9px; }}
                        .condic-list {{ font-size: 8px; text-align: justify; margin: 2px 0; line-height: 1.15; }}
                        .cut-line {{
                            border-top: 1.5px dashed #444;
                            margin: 10px 0;
                            text-align: center;
                            position: relative;
                        }}
                        .cut-line span {{
                            background: #fff;
                            padding: 0 8px;
                            font-size: 8px;
                            font-weight: bold;
                            color: #444;
                            position: relative;
                            top: -6px;
                        }}
                        .btn-print {{ background-color: #2563eb; color: #fff; border: none; padding: 10px 20px; font-size: 12px; font-weight: bold; cursor: pointer; border-radius: 6px; margin-bottom: 10px; text-transform: uppercase; }}
                        @media print {{ 
                            .btn-print {{ display: none !important; }} 
                            body {{ padding: 0; margin: 0; }}
                            .os-box {{ page-break-inside: avoid; }}
                        }}
                    </style>
                </head>
                <body>
                    <button class="btn-print" onclick="window.print()">IMPRIMIR COMPROVANTE (2 VIAS NA A4)</button>
                    <div class="page-container">
                        {gerar_via_entrada("VIA DO CLIENTE")}
                        <div class="cut-line">
                            <span>✂ DESTACAR AQUI — VIA DA EMPRESA ABAIXO ✂</span>
                        </div>
                        {gerar_via_entrada("VIA DA EMPRESA")}
                    </div>
                </body>
                </html>
                """
            else:
                html_documento = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <style>
                        @page {{ size: auto; margin: 10mm; }}
                        body {{ font-family: Arial, Helvetica, sans-serif; font-size: 12px; color: #000; background-color: #fff; margin: 0; padding: 10px; }}
                        .os-box {{ border: 1px solid #000; padding: 15px; background: #fff; position: relative; overflow: hidden; }}
                        .watermark {{
                            position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
                            opacity: 0.08; pointer-events: none; z-index: 0; width: 65%; max-width: 450px;
                        }}
                        .os-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #000; padding-bottom: 8px; margin-bottom: 10px; position: relative; z-index: 1; }}
                        .os-title {{ text-align: center; font-weight: bold; font-size: 14px; margin: 10px 0; border-top: 1px solid #000; border-bottom: 1px solid #000; padding: 4px 0; position: relative; z-index: 1; }}
                        .os-section {{ border-bottom: 1px dashed #777; padding: 6px 0; position: relative; z-index: 1; }}
                        .os-grid-2 {{ display: flex; justify-content: space-between; position: relative; z-index: 1; }}
                        .os-grid-3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; position: relative; z-index: 1; }}
                        .signature-line {{ border-top: 1px solid #000; margin-top: 35px; text-align: center; }}
                        .btn-print {{ background-color: #2563eb; color: #fff; border: none; padding: 12px 24px; font-size: 13px; font-weight: bold; cursor: pointer; border-radius: 6px; margin-bottom: 15px; text-transform: uppercase; }}
                        @media print {{ .btn-print {{ display: none !important; }} body {{ padding: 0; }} }}
                    </style>
                </head>
                <body>
                    <button class="btn-print" onclick="window.print()">IMPRIMIR COMPROVANTE DE SAÍDA</button>
                    <div class="os-box">
                        {watermark_html}
                        <div class="os-header">
                            <div style="display: flex; align-items: center;">
                                {logo_html}
                                <div>
                                    <strong style="font-size: 16px;">{empresa_nome}</strong><br>
                                    <small>{empresa_end}</small><br>
                                    <small>{empresa_email}</small>
                                </div>
                            </div>
                            <div style="text-align: right;">
                                <strong>{empresa_tel}</strong><br>
                                <strong>CNPJ {empresa_cnpj}</strong>
                            </div>
                        </div>
                        <div class="os-grid-2">
                            <div><strong style="font-size: 15px;">ORDEM DE SERVIÇO Nº {d[1]}</strong></div>
                            <div style="text-align: right;">Hora: {d[3]} &nbsp;&nbsp; Data: {d[2]}</div>
                        </div>
                        <div style="border: 1px solid #000; padding: 6px; margin: 8px 0; position: relative; z-index: 1;">
                            <strong>Cliente:</strong> {d[5]} &nbsp;&nbsp;&nbsp;&nbsp; <strong>Contato:</strong> {d[8]} &nbsp;&nbsp;&nbsp;&nbsp; <strong>Tel:</strong> {d[9]}<br>
                            <strong>Endereço:</strong> {d[6]}<br>
                            <strong>CPF/CNPJ:</strong> {d[7]} &nbsp;&nbsp; <strong>Bairro:</strong> {d[10]} &nbsp;&nbsp; <strong>Cidade:</strong> {d[11]}
                        </div>
                        <div class="os-title">COMPROVANTE DE SAÍDA - TERMOS DE GARANTIA</div>
                        <div class="os-section">
                            <div class="os-grid-3">
                                <div><strong>Equipamento:</strong> {d[14]}</div>
                                <div><strong>Modelo:</strong> {d[15]}</div>
                                <div><strong>Marca:</strong> {d[16]}</div>
                            </div>
                            <div class="os-grid-2" style="margin-top: 4px;">
                                <div><strong>Acessórios:</strong> {d[17]}</div>
                                <div><strong>Série/Tag:</strong> {d[18]}</div>
                            </div>
                        </div>
                        <div class="os-section">
                            <strong>Problema Informado:</strong><br>
                            <span>{d[19] or 'N/A'}</span><br><br>
                            <strong>Problema Constatado:</strong><br>
                            <span>{d[20] or 'N/A'}</span>
                        </div>
                        <div class="os-section">
                            <strong>Serviço Executado:</strong><br>
                            <span>{d[21] or 'N/A'}</span>
                        </div>
                        <div class="os-section">
                            <strong>SOBRE A GARANTIA DO SERVIÇO:</strong><br>
                            <strong>{d[22] or 'N/A'}</strong>
                        </div>
                        <div style="margin: 12px 0; font-weight: bold; text-align: center; position: relative; z-index: 1;">
                            VIOLAÇÃO DE LACRE OCASIONA PERDA DA GARANTIA!
                        </div>
                        <div class="os-grid-2" style="border-top: 1px solid #000; padding-top: 8px;">
                            <div>
                                <strong>Responsável:</strong> {d[23]}<br>
                                <strong>Situação:</strong> {d[24]}<br>
                                <strong>Data Saída:</strong> {d[25]} &nbsp; <strong>Forma:</strong> {d[27]}<br>
                                <strong>Hora Saída:</strong> {d[26]} &nbsp; <strong>Condições:</strong> {d[28]}
                            </div>
                            <div style="text-align: right; line-height: 1.5;">
                                VALOR PRODUTOS R$ &nbsp;&nbsp;&nbsp;&nbsp; {float(d[29] or 0):.2f}<br>
                                VALOR SERVIÇOS R$ &nbsp;&nbsp;&nbsp;&nbsp; {float(d[30] or 0):.2f}<br>
                                DESLOCAMENTO R$ &nbsp;&nbsp;&nbsp;&nbsp; {float(d[31] or 0):.2f}<br>
                                VALOR DESCONTO R$ &nbsp;&nbsp;&nbsp;&nbsp; {float(d[32] or 0):.2f}<br>
                                <strong>VALOR TOTAL R$ &nbsp;&nbsp;&nbsp;&nbsp; {float(d[33] or 0):.2f}</strong>
                            </div>
                        </div>
                        <div style="margin-top: 30px; position: relative; z-index: 1;">
                            <strong>Técnico Responsável:</strong> {d[23]}
                            <div class="os-grid-2" style="margin-top: 25px;">
                                <div style="width: 45%;" class="signature-line">Assinatura Técnico</div>
                                <div style="width: 45%;" class="signature-line">Assinatura Cliente</div>
                            </div>
                        </div>
                        <div style="margin-top: 15px; font-size: 10px; position: relative; z-index: 1;">
                            (X) Via do Cliente &nbsp;&nbsp;&nbsp;&nbsp; ( ) Via da Empresa
                        </div>
                    </div>
                </body>
                </html>
                """

            st.components.v1.html(html_documento, height=950, scrolling=True)
        else:
            st.error("O.S. não encontrada.")

# --- CRIAR ORÇAMENTO ---
elif menu_principal == "Criar Orçamento Comercial":
    st.caption("Monte e cadastre orçamentos comerciais completos")

    if "itens_orcamento" not in st.session_state:
        st.session_state["itens_orcamento"] = []

    cursor.execute("SELECT id_cliente, nome, cpf_cnpj, telefone, endereco, cidade, uf FROM clientes ORDER BY nome ASC")
    lista_cli = cursor.fetchall()
    opcoes_cli = ["-- Selecionar Cliente Cadastrado ou Digitar Abaixo --"] + [f"{c[1]} | {c[2] or 'Sem CPF'}" for c in lista_cli]

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    cli_sel = st.selectbox("Buscar Cliente Cadastrado:", opcoes_cli)
    
    c_nome, c_cpf, c_tel, c_end, c_cid = "", "", "", "", "BRASÍLIA / DF"
    c_id = None

    if cli_sel != "-- Selecionar Cliente Cadastrado ou Digitar Abaixo --":
        idx = opcoes_cli.index(cli_sel) - 1
        d_cli = lista_cli[idx]
        c_id, c_nome, c_cpf, c_tel = d_cli[0], d_cli[1] or "", d_cli[2] or "", d_cli[3] or ""
        c_end = f"{d_cli[4] or ''}".strip()
        c_cid = f"{d_cli[5] or ''} / {d_cli[6] or ''}".strip()

    st.markdown('</div>', unsafe_allow_html=True)

    st.subheader("1. Identificação da Proposta")
    c_p1, c_p2, c_p3, c_p4 = st.columns(4)
    num_orc_sug = f"ORC{datetime.now().strftime('%Y%m%d%H%M')}"
    numero_orc = c_p1.text_input("Número da Proposta *", num_orc_sug)
    data_emissao = c_p2.date_input("Data de Emissão").strftime("%d/%m/%Y")
    dias_validade = c_p3.number_input("Validade (Dias)", value=15, step=1)
    data_validade = (datetime.now() + timedelta(days=dias_validade)).strftime("%d/%m/%Y")
    c_p4.text_input("Válido até:", data_validade, disabled=True)

    st.markdown("---")
    st.subheader("2. Dados do Cliente")
    c_c1, c_c2, c_c3 = st.columns(3)
    cliente_nome = c_c1.text_input("Cliente / Razão Social *", value=c_nome)
    cliente_cpf = c_c2.text_input("CPF / CNPJ", value=c_cpf)
    cliente_tel = c_c3.text_input("Telefone / WhatsApp", value=c_tel)

    equipamento_ref = st.text_input("Equipamento / Projeto de Referência", "Notebook / Computador")

    st.markdown("---")
    st.subheader("3. Especificação dos Itens")

    cursor.execute("SELECT id_item, tipo, descricao, preco_venda FROM itens_catalogo ORDER BY descricao ASC")
    itens_cadastrados = cursor.fetchall()
    opcoes_cat = ["-- Digitar Manualmente Abaixo --"] + [f"[{i[1]}] {i[2]} - R$ {float(i[3] or 0):.2f}" for i in itens_cadastrados]

    item_cat_sel = st.selectbox("Selecionar Item do Catálogo de Preços:", opcoes_cat)
    
    val_unit_sug = 0.0
    desc_sug = ""
    tipo_sug = "Serviço"

    if item_cat_sel != "-- Digitar Manualmente Abaixo --":
        idx_cat = opcoes_cat.index(item_cat_sel) - 1
        i_cat = itens_cadastrados[idx_cat]
        tipo_sug = i_cat[1]
        desc_sug = i_cat[2]
        val_unit_sug = float(i_cat[3] or 0.0)

    col_i1, col_i2, col_i3, col_i4, col_i5 = st.columns([1.5, 3, 1, 1.5, 1])
    tipo_item = col_i1.selectbox("Tipo", ["Serviço", "Produto"], index=0 if tipo_sug == "Serviço" else 1)
    desc_item = col_i2.text_input("Descrição do Item", value=desc_sug)
    qtd_item = col_i3.number_input("Qtd", min_value=1.0, value=1.0, step=1.0)
    vunit_item = col_i4.number_input("Valor Unitário (R$)", min_value=0.0, value=val_unit_sug, step=10.0)
    
    if col_i5.button("Incluir"):
        if desc_item and vunit_item > 0:
            tot_i = qtd_item * vunit_item
            st.session_state["itens_orcamento"].append({
                "tipo": tipo_item, "descricao": desc_item,
                "qtd": qtd_item, "val_unitario": vunit_item, "val_total": tot_i
            })
            st.rerun()
        else:
            st.warning("Informe a descrição e um valor maior que zero.")

    if st.session_state["itens_orcamento"]:
        df_itens = pd.DataFrame(st.session_state["itens_orcamento"])
        st.markdown("##### Itens Inseridos na Proposta:")
        st.dataframe(df_itens, use_container_width=True)
        
        if st.button("Remover Todos os Itens"):
            st.session_state["itens_orcamento"] = []
            st.rerun()

    subtotal_orc = sum(i["val_total"] for i in st.session_state["itens_orcamento"])
    
    st.markdown("---")
    st.subheader("4. Fechamento Comercial e Garantia")
    col_f1, col_f2, col_f3 = st.columns(3)
    val_desconto = col_f1.number_input("Desconto (R$)", min_value=0.0, value=0.0, step=10.0)
    cond_pagamento = col_f2.text_input("Condições de Pagamento", "PIX / Cartão até 3x sem juros")
    prazo_entrega = col_f3.text_input("Prazo de Execução", "1 a 3 dias úteis após aprovação")

    obs_orcamento = st.text_area("Termos de Garantia e Condições de Serviços", value=TEXTO_GARANTIA_ORCAMENTO, height=140)

    val_total_final = max(0.0, subtotal_orc - val_desconto)
    st.success(f"VALOR TOTAL CALCULADO: R$ {val_total_final:.2f}")

    if st.button("SALVAR E EMITIR PROPOSTA"):
        if not cliente_nome or not numero_orc:
            st.error("Preencha ao menos o Nome do Cliente e o Número do Orçamento.")
        elif not st.session_state["itens_orcamento"]:
            st.error("Adicione ao menos um produto ou serviço à proposta.")
        else:
            cursor.execute("""
                INSERT INTO orcamentos (
                    numero_orcamento, data_emissao, data_validade, cliente_id, cliente_nome,
                    cliente_cpf_cnpj, cliente_tel, equipamento, observacoes, condicoes_pagamento,
                    prazo_entrega, val_subtotal, val_desconto, val_total, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pendente')
            """, (
                numero_orc, data_emissao, data_validade, c_id, cliente_nome,
                cliente_cpf, cliente_tel, equipamento_ref, obs_orcamento, cond_pagamento,
                prazo_entrega, subtotal_orc, val_desconto, val_total_final
            ))
            id_orc_gerado = cursor.lastrowid

            for it in st.session_state["itens_orcamento"]:
                cursor.execute("""
                    INSERT INTO orcamento_itens (orcamento_id, tipo, descricao, qtd, val_unitario, val_total_item)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (id_orc_gerado, it["tipo"], it["descricao"], it["qtd"], it["val_unitario"], it["val_total"]))

            conn.commit()
            st.session_state["itens_orcamento"] = []
            st.success(f"Proposta Comercial Nº {numero_orc} salva com sucesso.")

# --- CONSULTAR ORÇAMENTO ---
elif menu_principal == "Consultar / Imprimir Orçamento":
    st.caption("Consulte e imprima orçamentos comerciais em PDF")

    df_busca = pd.read_sql_query("""
        SELECT id_orcamento AS 'ID', numero_orcamento AS 'Nº Orçamento', cliente_nome AS 'Cliente', 
               data_emissao AS 'Emissão', data_validade AS 'Validade', val_total AS 'Total (R$)', status AS 'Status'
        FROM orcamentos ORDER BY id_orcamento DESC
    """, conn)
    st.dataframe(df_busca, use_container_width=True)

    col_s1, col_s2 = st.columns([2, 1])
    id_orc_sel = col_s1.number_input("Digite o ID do Orçamento para visualizar:", min_value=1, step=1)

    if col_s2.button("Visualizar Orçamento"):
        cursor.execute("SELECT * FROM orcamentos WHERE id_orcamento = ?", (id_orc_sel,))
        orc = cursor.fetchone()

        if orc:
            cursor.execute("SELECT tipo, descricao, qtd, val_unitario, val_total_item FROM orcamento_itens WHERE orcamento_id = ?", (id_orc_sel,))
            itens = cursor.fetchall()

            linhas_itens_html = ""
            for item in itens:
                qtd_v = float(item[2] or 0.0)
                vunit_v = float(item[3] or 0.0)
                vtot_v = float(item[4] or 0.0)
                linhas_itens_html += f"""
                <tr>
                    <td style="padding: 6px; border: 1px solid #ccc;">{item[0]}</td>
                    <td style="padding: 6px; border: 1px solid #ccc;">{item[1]}</td>
                    <td style="padding: 6px; border: 1px solid #ccc; text-align: center;">{qtd_v:.0f}</td>
                    <td style="padding: 6px; border: 1px solid #ccc; text-align: right;">R$ {vunit_v:.2f}</td>
                    <td style="padding: 6px; border: 1px solid #ccc; text-align: right;">R$ {vtot_v:.2f}</td>
                </tr>
                """

            subtotal_val = float(orc[14] or 0.0)
            desconto_val = float(orc[15] or 0.0)
            total_val = float(orc[16] or 0.0)
            obs_formatada = (orc[11] or TEXTO_GARANTIA_ORCAMENTO).replace('\n', '<br>')

            html_orcamento = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    @page {{ size: auto; margin: 10mm; }}
                    body {{ font-family: Arial, Helvetica, sans-serif; font-size: 11px; color: #000; background-color: #fff; margin: 0; padding: 10px; line-height: 1.4; }}
                    .box {{ border: 1px solid #000; padding: 15px; background: #fff; position: relative; overflow: hidden; }}
                    .watermark {{
                        position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
                        opacity: 0.08; pointer-events: none; z-index: 0; width: 65%; max-width: 450px;
                    }}
                    .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #000; padding-bottom: 8px; margin-bottom: 10px; position: relative; z-index: 1; }}
                    .title {{ text-align: center; font-weight: bold; font-size: 14px; margin: 10px 0; border-top: 1px solid #000; border-bottom: 1px solid #000; padding: 4px 0; position: relative; z-index: 1; }}
                    .grid-2 {{ display: flex; justify-content: space-between; position: relative; z-index: 1; }}
                    .table-itens {{ width: 100%; border-collapse: collapse; margin: 10px 0; position: relative; z-index: 1; }}
                    .table-itens th {{ background-color: #f2f2f2; padding: 6px; border: 1px solid #000; text-align: left; font-size: 11px; }}
                    .content-section {{ position: relative; z-index: 1; }}
                    .btn-print {{ background-color: #2563eb; color: #fff; border: none; padding: 12px 24px; font-size: 13px; font-weight: bold; cursor: pointer; border-radius: 6px; margin-bottom: 15px; text-transform: uppercase; }}
                    .termo-box {{ font-size: 10px; text-align: justify; line-height: 1.4; background: #fafafa; padding: 8px; border: 1px solid #ddd; margin-top: 5px; }}
                    @media print {{ .btn-print {{ display: none !important; }} body {{ padding: 0; }} }}
                </style>
            </head>
            <body>
                <button class="btn-print" onclick="window.print()">IMPRIMIR / SALVAR PROPOSTA EM PDF</button>
                <div class="box">
                    {watermark_html}
                    <div class="header">
                        <div style="display: flex; align-items: center;">
                            {logo_html}
                            <div>
                                <strong style="font-size: 16px;">{empresa_nome}</strong><br>
                                <small>{empresa_end}</small><br>
                                <small>{empresa_email}</small>
                            </div>
                        </div>
                        <div style="text-align: right;">
                            <strong>{empresa_tel}</strong><br>
                            <strong>CNPJ {empresa_cnpj}</strong>
                        </div>
                    </div>

                    <div class="title">PROPOSTA COMERCIAL / ORÇAMENTO Nº {orc[1]}</div>

                    <div class="grid-2" style="border: 1px solid #000; padding: 8px; margin-bottom: 10px;">
                        <div>
                            <strong>Cliente:</strong> {orc[5]}<br>
                            <strong>CPF/CNPJ:</strong> {orc[6] or 'N/A'}<br>
                            <strong>Telefone:</strong> {orc[7] or 'N/A'}
                        </div>
                        <div style="text-align: right;">
                            <strong>Data Emissão:</strong> {orc[2]}<br>
                            <strong>Validade até:</strong> {orc[3]}<br>
                            <strong>Ref. Equipamento:</strong> {orc[10] or 'Diversos'}
                        </div>
                    </div>

                    <div class="content-section">
                        <strong style="font-size: 12px;">ESPECIFICAÇÃO DOS PRODUTOS E SERVIÇOS:</strong>
                    </div>
                    
                    <table class="table-itens">
                        <thead>
                            <tr>
                                <th style="width: 15%;">Tipo</th>
                                <th>Descrição do Item</th>
                                <th style="width: 10%; text-align: center;">Qtd</th>
                                <th style="width: 15%; text-align: right;">Valor Unit.</th>
                                <th style="width: 15%; text-align: right;">Subtotal</th>
                            </tr>
                        </thead>
                        <tbody>
                            {linhas_itens_html}
                        </tbody>
                    </table>

                    <div class="grid-2" style="border-top: 1px solid #000; padding-top: 8px; margin-top: 10px;">
                        <div style="width: 58%;">
                            <strong>Condições de Pagamento:</strong> {orc[12] or 'À Vista'}<br>
                            <strong>Prazo de Entrega:</strong> {orc[13] or 'A combinar'}<br><br>
                            <strong>TERMOS DE GARANTIA E SERVIÇOS:</strong>
                            <div class="termo-box">
                                {obs_formatada}
                            </div>
                        </div>
                        <div style="text-align: right; line-height: 1.6; width: 38%;">
                            Subtotal R$: {subtotal_val:.2f}<br>
                            Desconto R$: {desconto_val:.2f}<br>
                            <strong style="font-size: 14px;">TOTAL PROPOSTA R$: {total_val:.2f}</strong>
                        </div>
                    </div>

                    <div class="content-section" style="margin-top: 40px; display: flex; justify-content: space-between;">
                        <div style="width: 45%; border-top: 1px solid #000; text-align: center; padding-top: 5px;">
                            {empresa_nome}<br>
                            <small>Responsável Técnico</small>
                        </div>
                        <div style="width: 45%; border-top: 1px solid #000; text-align: center; padding-top: 5px;">
                            Aprovado por: {orc[5]}<br>
                            <small>Assinatura de Aceite do Cliente</small>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            st.components.v1.html(html_orcamento, height=850, scrolling=True)
        else:
            st.error("Orçamento não encontrado.")

# --- BASE DE CLIENTES ---
elif menu_principal == "Base de Clientes":
    st.caption("Consulte a base de clientes cadastrados no sistema")
    df_clientes = pd.read_sql_query("""
        SELECT id_cliente AS 'ID', nome AS 'Nome / Razão Social', cpf_cnpj AS 'CPF/CNPJ', 
               telefone AS 'Telefone', contato AS 'Contato', bairro AS 'Bairro', cidade AS 'Cidade', uf AS 'UF'
        FROM clientes ORDER BY nome ASC
    """, conn)
    st.dataframe(df_clientes, use_container_width=True)

# --- CATÁLOGO ---
elif menu_principal == "Catálogo de Produtos e Serviços":
    st.caption("Cadastre produtos e serviços para reutilização ágil")

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Novo Item no Catálogo")
    
    with st.form("form_cad_item"):
        col_cat1, col_cat2, col_cat3, col_cat4 = st.columns([1, 2.5, 1, 1])
        tipo_cat = col_cat1.selectbox("Tipo *", ["Serviço", "Produto"])
        desc_cat = col_cat2.text_input("Descrição do Produto / Serviço *", placeholder="ex: Formatação c/ Backup")
        preco_cat = col_cat3.number_input("Preço de Venda (R$) *", min_value=0.0, step=10.0)
        estq_cat = col_cat4.number_input("Qtd Estoque", min_value=0.0, step=1.0, value=0.0)
        
        btn_cad = st.form_submit_button("Salvar no Catálogo")
        if btn_cad:
            if desc_cat and preco_cat >= 0:
                cursor.execute("""
                    INSERT INTO itens_catalogo (tipo, descricao, preco_venda, estoque_qtd)
                    VALUES (?, ?, ?, ?)
                """, (tipo_cat, desc_cat, preco_cat, estq_cat))
                conn.commit()
                st.success(f"'{desc_cat}' cadastrado no catálogo com sucesso.")
                st.rerun()
            else:
                st.error("Preencha a descrição do item.")

    st.markdown('</div>', unsafe_allow_html=True)

    st.subheader("Itens Cadastrados")
    df_cat = pd.read_sql_query("""
        SELECT id_item AS 'ID', tipo AS 'Tipo', descricao AS 'Descrição', 
               preco_venda AS 'Preço Venda (R$)', estoque_qtd AS 'Qtd Estoque'
        FROM itens_catalogo ORDER BY tipo ASC, descricao ASC
    """, conn)
    st.dataframe(df_cat, use_container_width=True)

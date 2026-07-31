import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import base64
import os
import requests
import re
import hashlib
import hmac
import mimetypes
from sqlalchemy import create_engine, text

# --- BUSCA PROFUNDA DA LOGO (FAVICON E INTERFACE) ---
diretorio_atual = os.path.dirname(os.path.abspath(__file__))
caminho_logo_encontrado = None
extensoes_validas = ('.png', '.jpg', '.jpeg', '.webp', '.svg')

for raiz, diretorios, arquivos in os.walk(diretorio_atual):
    for arquivo in arquivos:
        nome_lower = arquivo.lower()
        if 'logo' in nome_lower and nome_lower.endswith(extensoes_validas):
            caminho_logo_encontrado = os.path.join(raiz, arquivo)
            break
    if caminho_logo_encontrado:
        break

# --- CONFIGURAÇÃO DA PÁGINA (FAVICON NA ABA DO NAVEGADOR) ---
st.set_page_config(
    page_title="Micro Fox Soluções em TI - Sistema Integrado de Gestão", 
    page_icon=caminho_logo_encontrado if caminho_logo_encontrado else "🛠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- TRATAMENTO HTML DA LOGO ---
logo_html, logo_banner_html, watermark_html = "", "", ""

if caminho_logo_encontrado:
    mime_type, _ = mimetypes.guess_type(caminho_logo_encontrado)
    if not mime_type:
        mime_type = "image/png"
        
    with open(caminho_logo_encontrado, "rb") as image_file:
        logo_b64 = base64.b64encode(image_file.read()).decode()
        src_data = f"data:{mime_type};base64,{logo_b64}"
        
        logo_html = f'<img src="{src_data}" style="max-height: 65px; max-width: 160px; margin-right: 15px;"/>'
        logo_banner_html = f'<img src="{src_data}" style="width: 85px; height: 85px; border-radius: 50%; object-fit: cover; border: 2px solid #ff8c00; margin-bottom: 5px;"/>'
        watermark_html = f'<img src="{src_data}" class="watermark"/>'

# --- CONEXÃO COM BANCO DE DADOS HÍBRIDO E TRATAMENTO DE ERRO ---
@st.cache_resource
def iniciar_conexao_banco():
    db_url = None
    
    # 1. Tenta buscar nas Secrets do Streamlit
    if "DATABASE_URL" in st.secrets and "postgres.xxx" not in st.secrets["DATABASE_URL"]:
        db_url = st.secrets["DATABASE_URL"]
    elif "DATABASE_URL" in os.environ and "postgres.xxx" not in os.environ["DATABASE_URL"]:
        db_url = os.environ["DATABASE_URL"]
    
    if db_url and "postgres.xxx" not in db_url:
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        
        if "supabase" in db_url and "sslmode" not in db_url:
            separador = "&" if "?" in db_url else "?"
            db_url = f"{db_url}{separador}sslmode=require"

        try:
            engine_pg = create_engine(db_url, pool_pre_ping=True, connect_args={"connect_timeout": 10})
            with engine_pg.connect() as conn:
                conn.execute(text("SELECT 1"))
            return engine_pg, "postgresql", None
        except Exception as e:
            engine_sq = create_engine("sqlite:///sistema_os.db", connect_args={"check_same_thread": False})
            return engine_sq, "sqlite_fallback", str(e)
    else:
        # Se a chave for inválida ou ainda contiver 'postgres.xxx', roda no SQLite local
        engine_sq = create_engine("sqlite:///sistema_os.db", connect_args={"check_same_thread": False})
        return engine_sq, "sqlite", "A variável DATABASE_URL nas Secrets ainda contém 'postgres.xxx' ou não foi configurada."

engine, TIPO_BANCO, ERRO_CONEXAO = iniciar_conexao_banco()

# Se houve erro ao tentar conectar no Postgres, exibe na tela para sabermos a causa
if ERRO_CONEXAO:
    st.error("⚠️ **Falha ao conectar no PostgreSQL (Supabase)**")
    st.warning(f"**Detalhe do Erro:** `{ERRO_CONEXAO}`")
    st.info("O sistema iniciou temporariamente em modo local (SQLite) para não ficar fora do ar.")

# --- CRIAÇÃO DAS TABELAS AUTOMÁTICA ---
def inicializar_tabelas():
    query_ddl = """
    CREATE TABLE IF NOT EXISTS clientes (
        id_cliente SERIAL PRIMARY KEY,
        nome VARCHAR(255) NOT NULL,
        cpf_cnpj VARCHAR(50),
        telefone VARCHAR(50),
        contato VARCHAR(255),
        endereco TEXT,
        bairro VARCHAR(100),
        cidade VARCHAR(100),
        uf VARCHAR(10),
        cep VARCHAR(20)
    );

    CREATE TABLE IF NOT EXISTS ordens_servico (
        id_os SERIAL PRIMARY KEY,
        numero_os VARCHAR(50),
        data_abertura VARCHAR(20),
        hora_abertura VARCHAR(20),
        cliente_id INTEGER,
        cliente_nome VARCHAR(255),
        cliente_endereco TEXT,
        cliente_cpf_cnpj VARCHAR(50),
        cliente_contato VARCHAR(255),
        cliente_tel VARCHAR(50),
        cliente_bairro VARCHAR(100),
        cliente_cidade VARCHAR(100),
        cliente_uf VARCHAR(10),
        cliente_cep VARCHAR(20),
        equipamento VARCHAR(255),
        modelo VARCHAR(255),
        marca VARCHAR(255),
        acessorios TEXT,
        numero_serie VARCHAR(100),
        problema_informado TEXT,
        problema_constatado TEXT,
        servico_executado TEXT,
        garantia_texto TEXT,
        responsavel VARCHAR(100),
        situacao VARCHAR(100),
        data_saida VARCHAR(20),
        hora_saida VARCHAR(20),
        forma_pagamento VARCHAR(100),
        condicoes VARCHAR(100),
        val_produtos NUMERIC(10, 2) DEFAULT 0.0,
        val_servicos NUMERIC(10, 2) DEFAULT 0.0,
        val_deslocamento NUMERIC(10, 2) DEFAULT 0.0,
        val_desconto NUMERIC(10, 2) DEFAULT 0.0,
        val_total NUMERIC(10, 2) DEFAULT 0.0,
        tipo_documento VARCHAR(100) DEFAULT 'Comprovante de Saída'
    );

    CREATE TABLE IF NOT EXISTS itens_catalogo (
        id_item SERIAL PRIMARY KEY,
        tipo VARCHAR(50) NOT NULL,
        descricao VARCHAR(255) NOT NULL,
        preco_venda NUMERIC(10, 2) DEFAULT 0.0,
        estoque_qtd NUMERIC(10, 2) DEFAULT 0.0
    );

    CREATE TABLE IF NOT EXISTS orcamentos (
        id_orcamento SERIAL PRIMARY KEY,
        numero_orcamento VARCHAR(50),
        data_emissao VARCHAR(20),
        data_validade VARCHAR(20),
        cliente_id INTEGER,
        cliente_nome VARCHAR(255),
        cliente_cpf_cnpj VARCHAR(50),
        cliente_tel VARCHAR(50),
        cliente_email VARCHAR(255),
        cliente_cidade VARCHAR(100),
        equipamento VARCHAR(255),
        observacoes TEXT,
        condicoes_pagamento VARCHAR(100),
        prazo_entrega VARCHAR(100),
        val_subtotal NUMERIC(10, 2) DEFAULT 0.0,
        val_desconto NUMERIC(10, 2) DEFAULT 0.0,
        val_total NUMERIC(10, 2) DEFAULT 0.0,
        status VARCHAR(50) DEFAULT 'Pendente'
    );

    CREATE TABLE IF NOT EXISTS orcamento_itens (
        id_item SERIAL PRIMARY KEY,
        orcamento_id INTEGER,
        tipo VARCHAR(50),
        descricao TEXT,
        qtd NUMERIC(10, 2) DEFAULT 1,
        val_unitario NUMERIC(10, 2) DEFAULT 0.0,
        val_total_item NUMERIC(10, 2) DEFAULT 0.0
    );
    """
    if "sqlite" in TIPO_BANCO:
        query_ddl = query_ddl.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
        query_ddl = query_ddl.replace("NUMERIC(10, 2)", "REAL")
    
    with engine.begin() as conn:
        for comando in query_ddl.split(";"):
            if comando.strip():
                conn.execute(text(comando))

inicializar_tabelas()

# --- CRIPTOGRAFIA DE LOGIN ---
def gerar_hash_senha(senha_texto_puro: str, salt: bytes = b"microfox_salt_seguro_2026") -> str:
    hash_bytes = hashlib.pbkdf2_hmac('sha256', senha_texto_puro.encode('utf-8'), salt, 100000)
    return hash_bytes.hex()

def verificar_senha(senha_digitada: str, hash_esperado: str) -> bool:
    return hmac.compare_digest(gerar_hash_senha(senha_digitada), hash_esperado)

USUARIO_CORRETO = "admin"
HASH_SENHA_CORRETA = gerar_hash_senha("microfox@123")

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

TEXTO_GARANTIA_ORCAMENTO = """GARANTIA DE EQUIPAMENTOS E SERVIÇOS
Forneceremos 01 (um) ano de garantia dos produtos e 03 (três) meses de garantia dos nossos serviços e consultoria gratuita pelo mesmo período.
Nos preços cotados não estão incluídos serviços de desobstrução e/ou substituição de tubulação que eventualmente se façam necessários, bem como obras civis associadas.
Qualquer outro tipo de serviço que seja necessário será informado com antecedência para que seja tomada as providencias cabíveis, será cobrado a taxa de 250,00 adicional."""

# --- ESTILIZAÇÃO CSS CUSTOMIZADA ---
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #0b0f19 0%, #111827 100%) !important; color: #f8fafc !important; }
    [data-testid="stSidebar"] { background: rgba(15, 23, 42, 0.75) !important; backdrop-filter: blur(12px); border-right: 1px solid rgba(255, 255, 255, 0.08); }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: #ff8c00 !important; font-weight: 700; }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] span, [data-testid="stSidebar"] p { color: #cbd5e1 !important; font-weight: 600; }
    [data-testid="stSidebar"] input { color: #0f172a !important; background-color: #ffffff !important; border-radius: 6px !important; }
    h1, h2, h3 { color: #ff8c00 !important; font-family: 'Inter', Arial, sans-serif; font-weight: 700; }
    .stMainBlockContainer label, .stMainBlockContainer p, .stMainBlockContainer caption { color: #cbd5e1 !important; font-weight: 600 !important; }
    .stMainBlockContainer input, .stMainBlockContainer textarea, .stMainBlockContainer select, div[data-baseweb="select"] span {
        color: #0f172a !important; background-color: #ffffff !important; font-weight: 500 !important;
    }
    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
        border-radius: 8px !important; border: 1px solid #334155 !important; background-color: #ffffff !important;
    }
    .metric-card {
        background: rgba(30, 41, 59, 0.6) !important; backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 12px; padding: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37); text-align: center;
    }
    .metric-title { font-size: 13px; color: #94a3b8 !important; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .metric-value { font-size: 24px; color: #ff8c00 !important; font-weight: 700; margin-top: 5px; }
    .stButton > button {
        background: linear-gradient(135deg, rgba(255, 140, 0, 0.85) 0%, rgba(255, 167, 38, 0.85) 100%) !important;
        color: #ffffff !important; font-weight: 700 !important; border-radius: 8px !important; padding: 8px 12px !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px;
        backdrop-filter: blur(5px); box-shadow: 0 4px 15px rgba(255, 140, 0, 0.25); transition: all 0.3s ease-in-out !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #ffa726 0%, #ff8c00 100%) !important;
        box-shadow: 0 6px 20px rgba(255, 140, 0, 0.5) !important; transform: translateY(-2px);
    }
    .section-card { background: rgba(30, 41, 59, 0.5); backdrop-filter: blur(12px); border-radius: 12px; padding: 24px; border: 1px solid rgba(255, 255, 255, 0.08); margin-bottom: 20px; }
    .hero-banner {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(30, 41, 59, 0.8) 100%);
        backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 14px; padding: 20px 30px; margin-bottom: 15px; display: flex; flex-direction: column; align-items: center; text-align: center;
    }
    .hero-title { font-size: 26px; font-weight: 700; color: #ff8c00; margin-top: 8px; text-transform: uppercase; }
    .hero-subtitle { font-size: 14px; color: #94a3b8; margin-top: 4px; }
    .centered-header { text-align: center; color: #ff8c00; font-weight: 700; margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)

# --- CONSULTA CNPJ ---
def consultar_cnpj_api(cnpj):
    cnpj_limpo = re.sub(r'\D', '', cnpj)
    if len(cnpj_limpo) == 14:
        try:
            res = requests.get(f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}", timeout=5)
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
        res = requests.get(f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{sigla_uf}/municipios?orderBy=nome", timeout=5).json()
        return [c["nome"] for c in res]
    except Exception:
        return ["BRASÍLIA", "SAMAMBAIA", "TAGUATINGA"] if sigla_uf == "DF" else ["Capital / Centro"]

# --- CARREGAMENTO DE LOGO (BUSCA PROFUNDA NO REPOSITÓRIO) ---
import mimetypes

diretorio_atual = os.path.dirname(os.path.abspath(__file__))

# Varre o diretório do projeto procurando qualquer arquivo de imagem que contenha 'logo' no nome
caminho_logo_encontrado = None
extensoes_validas = ('.png', '.jpg', '.jpeg', '.webp', '.svg')

for raiz, diretorios, arquivos in os.walk(diretorio_atual):
    for arquivo in arquivos:
        nome_lower = arquivo.lower()
        if 'logo' in nome_lower and nome_lower.endswith(extensoes_validas):
            caminho_logo_encontrado = os.path.join(raiz, arquivo)
            break
    if caminho_logo_encontrado:
        break

logo_html, logo_banner_html, watermark_html = "", "", ""

if caminho_logo_encontrado:
    mime_type, _ = mimetypes.guess_type(caminho_logo_encontrado)
    if not mime_type:
        mime_type = "image/png"
        
    with open(caminho_logo_encontrado, "rb") as image_file:
        logo_b64 = base64.b64encode(image_file.read()).decode()
        src_data = f"data:{mime_type};base64,{logo_b64}"
        
        logo_html = f'<img src="{src_data}" style="max-height: 65px; max-width: 160px; margin-right: 15px;"/>'
        logo_banner_html = f'<img src="{src_data}" style="width: 85px; height: 85px; border-radius: 50%; object-fit: cover; border: 2px solid #ff8c00; margin-bottom: 5px;"/>'
        watermark_html = f'<img src="{src_data}" class="watermark"/>'
else:
    # Caso não ache o arquivo com a palavra 'logo', exibe lista para depuração
    arquivos_no_dir = os.listdir(diretorio_atual)
    st.sidebar.caption(f"⚠️ Imagem da logo não localizada. Arquivos na raiz: {arquivos_no_dir}")

# --- TELA DE LOGIN ---
if not st.session_state["autenticado"]:
    col_l1, col_l2, col_l3 = st.columns([1, 1.5, 1])
    with col_l2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        # Inserido o logo_banner_html na tela de login
        st.markdown(f'''
            <div style="text-align: center; background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(16px); padding: 30px; border-radius: 14px; border: 1px solid rgba(255, 255, 255, 0.12);">
                {logo_banner_html}
                <h2 style="color: #ff8c00; margin-top: 10px;">MICRO FOX SOLUÇÕES EM TI</h2>
                <p style="color: #94a3b8; font-size: 13px;">SISTEMA CORPORATIVO DE O.S. E ORÇAMENTOS</p>
            </div>
        ''', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        with st.form("form_login"):
            usuario = st.text_input("Usuário de Acesso")
            senha = st.text_input("Senha", type="password")
            if st.form_submit_button("ACESSAR SISTEMA", use_container_width=True):
                if usuario == USUARIO_CORRETO and verificar_senha(senha, HASH_SENHA_CORRETA):
                    st.session_state["autenticado"] = True
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
    st.stop()

# --- BARRA LATERAL ---
st.sidebar.markdown("### Dados da Empresa")
empresa_nome = st.sidebar.text_input("Razão Social", "MICRO FOX SOLUÇÕES E SERVIÇOS EM TI")
empresa_end = st.sidebar.text_input("Endereço/Cidade", "QN 312 CJ 4 LT 2 SAMAMBAIA - SUL - BRASÍLIA-DF")
empresa_cnpj = st.sidebar.text_input("CNPJ", "18.710.097/0001-91")
empresa_tel = st.sidebar.text_input("Telefone", "(61) 3246-6001")
empresa_email = st.sidebar.text_input("E-mail", "atendimento@microfox.com.br")


st.sidebar.caption(f"Banco Conectado: **{TIPO_BANCO.upper()}**")
st.sidebar.markdown("---")
if st.sidebar.button("Encerrar Sessão", use_container_width=True):
    st.session_state["autenticado"] = False
    st.rerun()

# --- BANNER SUPERIOR E NAVEGAÇÃO ---
st.markdown(f'<div class="hero-banner">{logo_banner_html}<div class="hero-title">MICRO FOX SOLUÇÕES EM TI</div><div class="hero-subtitle">Sistema Integrado de Ordens de Serviço e Propostas Comerciais</div></div>', unsafe_allow_html=True)

if "menu_principal_nav" not in st.session_state:
    st.session_state["menu_principal_nav"] = "Dashboard"

cols = st.columns(7)
modulos = ["Dashboard", "Nova O.S.", "Buscar O.S.", "Novo Orçamento", "Buscar Orçamentos", "Clientes", "Catálogo"]
modulos_map = {
    "Dashboard": "Dashboard", "Nova O.S.": "Criar O.S.", "Buscar O.S.": "Consultar O.S.",
    "Novo Orçamento": "Criar Orçamento", "Buscar Orçamentos": "Consultar Orçamento",
    "Clientes": "Clientes", "Catálogo": "Catálogo"
}

for col, rotulo in zip(cols, modulos):
    if col.button(rotulo, use_container_width=True):
        st.session_state["menu_principal_nav"] = modulos_map[rotulo]
        st.rerun()

st.markdown("<hr style='border: 1px solid rgba(255, 255, 255, 0.1); margin-top: 10px; margin-bottom: 20px;'>", unsafe_allow_html=True)
menu_principal = st.session_state["menu_principal_nav"]

# ==============================================================================
# DASHBOARD
# ==============================================================================
# ==============================================================================
# RENDERIZAÇÃO DAS TELAS / MÓDULOS
# ==============================================================================

if menu_principal == "Dashboard":
    st.subheader("Painel Geral")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Últimas Ordens de Serviço")
        try:
            df_os = pd.read_sql_query(text('''SELECT numero_os AS "Nº OS", cliente_nome AS "Cliente", equipamento AS "Equipamento", val_total AS "Total (R$)" FROM ordens_servico ORDER BY id_os DESC LIMIT 5'''), engine)
            st.dataframe(df_os, use_container_width=True)
        except Exception as e:
            st.info("Nenhuma ordem de serviço registrada ou tabela vazia.")

    with col2:
        st.markdown("### Últimos Orçamentos")
        try:
            df_orc = pd.read_sql_query(text('''SELECT numero_orcamento AS "Nº Proposta", cliente_nome AS "Cliente", val_total AS "Total (R$)", status AS "Status" FROM orcamentos ORDER BY id_orcamento DESC LIMIT 5'''), engine)
            st.dataframe(df_orc, use_container_width=True)
        except Exception as e:
            st.info("Nenhum orçamento registrado ou tabela vazia.")

elif menu_principal == "Criar O.S.":
    st.subheader("Nova Ordem de Serviço")
    st.info("Formulário de criação de O.S.")

elif menu_principal == "Consultar O.S.":
    st.subheader("Consultar / Buscar O.S.")
    st.info("Painel de busca de Ordens de Serviço.")

elif menu_principal == "Criar Orçamento":
    st.subheader("Novo Orçamento")
    st.info("Formulário de criação de Orçamento.")

elif menu_principal == "Consultar Orçamento":
    st.subheader("Consultar / Buscar Orçamentos")
    st.info("Painel de busca de Orçamentos.")

elif menu_principal == "Clientes":
    st.caption("Base de Clientes")
    try:
        df_cli = pd.read_sql_query(text('''SELECT id_cliente AS "ID", nome AS "Nome", cpf_cnpj AS "CPF/CNPJ", telefone AS "Telefone", cidade AS "Cidade", uf AS "UF" FROM clientes ORDER BY nome ASC'''), engine)
        st.dataframe(df_cli, use_container_width=True)
    except Exception as e:
        st.info("Base de clientes vazia ou não inicializada.")

elif menu_principal == "Catálogo":
    st.caption("Catálogo de Produtos e Serviços")
    with st.form("form_cat"):
        c1, c2, c3 = st.columns([1, 2, 1])
        tipo = c1.selectbox("Tipo", ["Serviço", "Produto"])
        desc = c2.text_input("Descrição")
        preco = c3.number_input("Preço Venda", min_value=0.0, step=10.0)
        if st.form_submit_button("Salvar no Catálogo"):
            if desc:
                with engine.begin() as conn:
                    conn.execute(text("INSERT INTO itens_catalogo (tipo, descricao, preco_venda) VALUES (:t, :d, :p)"), {"t": tipo, "d": desc, "p": preco})
                st.success("Item salvo!")
                st.rerun()

    try:
        df_cat = pd.read_sql_query(text('''SELECT id_item AS "ID", tipo AS "Tipo", descricao AS "Descrição", preco_venda AS "Preço (R$)" FROM itens_catalogo ORDER BY descricao ASC'''), engine)
        st.dataframe(df_cat, use_container_width=True)
    except Exception as e:
        st.info("Catálogo vazio ou não inicializado.")

# ==============================================================================
# BASE DE CLIENTES
# ==============================================================================
elif menu_principal == "Clientes":
    st.caption("Base de Clientes")
    df_cli = pd.read_sql_query(text('''SELECT id_cliente AS "ID", nome AS "Nome", cpf_cnpj AS "CPF/CNPJ", telefone AS "Telefone", cidade AS "Cidade", uf AS "UF" FROM clientes ORDER BY nome ASC'''), engine)
    st.dataframe(df_cli, use_container_width=True)

# ==============================================================================
# CATÁLOGO DE SERVIÇOS
# ==============================================================================
elif menu_principal == "Catálogo":
    st.caption("Catálogo de Produtos e Serviços")
    with st.form("form_cat"):
        c1, c2, c3 = st.columns([1, 2, 1])
        tipo = c1.selectbox("Tipo", ["Serviço", "Produto"])
        desc = c2.text_input("Descrição")
        preco = c3.number_input("Preço Venda", min_value=0.0, step=10.0)
        if st.form_submit_button("Salvar no Catálogo"):
            if desc:
                with engine.begin() as conn:
                    conn.execute(text("INSERT INTO itens_catalogo (tipo, descricao, preco_venda) VALUES (:t, :d, :p)"), {"t": tipo, "d": desc, "p": preco})
                st.success("Item salvo!")
                st.rerun()

    df_cat = pd.read_sql_query(text('''SELECT id_item AS "ID", tipo AS "Tipo", descricao AS "Descrição", preco_venda AS "Preço (R$)" FROM itens_catalogo ORDER BY descricao ASC'''), engine)
    st.dataframe(df_cat, use_container_width=True)

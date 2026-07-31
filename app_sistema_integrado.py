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

# ==============================================================================
# 1. BUSCA DE LOGO E CONFIGURAÇÃO DA PÁGINA (FAVICON)
# ==============================================================================
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

st.set_page_config(
    page_title="Micro Fox Soluções em TI - Sistema Integrado", 
    page_icon=caminho_logo_encontrado if caminho_logo_encontrado else "🛠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 2. TRATAMENTO HTML E EMBED DE IMAGEM DA LOGO
# ==============================================================================
logo_html, logo_banner_html, watermark_html = "", "", ""

if caminho_logo_encontrado:
    mime_type, _ = mimetypes.guess_type(caminho_logo_encontrado)
    if not mime_type:
        mime_type = "image/png"
        
    with open(caminho_logo_encontrado, "rb") as image_file:
        logo_b64 = base64.b64encode(image_file.read()).decode()
        src_data = f"data:{mime_type};base64,{logo_b64}"
        
        logo_html = f'<img src="{src_data}" style="max-height: 65px; max-width: 160px; margin-right: 15px;"/>'
        logo_banner_html = f'<img src="{src_data}" style="width: 85px; height: 85px; border-radius: 50%; object-fit: cover; border: 2px solid #ff8c00; margin-bottom: 10px;"/>'
        watermark_html = f'<img src="{src_data}" class="watermark"/>'

# ==============================================================================
# 3. BANCO DE DADOS (POSTGRESQL COM FALLBACK SQLITE)
# ==============================================================================
@st.cache_resource
def iniciar_conexao_banco():
    db_url = None
    
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
        engine_sq = create_engine("sqlite:///sistema_os.db", connect_args={"check_same_thread": False})
        return engine_sq, "sqlite", "DATABASE_URL não configurada ou inválida."

engine, tipo_banco, erro_banco = iniciar_conexao_banco()

# Criação automatizada das tabelas no banco caso não existam
with engine.begin() as conn:
    conn.execute(text('''
        CREATE TABLE IF NOT EXISTS clientes (
            id_cliente SERIAL PRIMARY KEY,
            nome VARCHAR(255) UNIQUE,
            cpf_cnpj VARCHAR(50),
            telefone VARCHAR(50),
            cidade VARCHAR(100),
            uf VARCHAR(10)
        );
    '''))
    conn.execute(text('''
        CREATE TABLE IF NOT EXISTS ordens_servico (
            id_os SERIAL PRIMARY KEY,
            numero_os VARCHAR(50) UNIQUE,
            cliente_nome VARCHAR(255),
            telefone VARCHAR(50),
            equipamento VARCHAR(255),
            num_serie VARCHAR(100),
            defeito_relatado TEXT,
            observacoes TEXT,
            status VARCHAR(50),
            val_servico NUMERIC(10,2),
            val_pecas NUMERIC(10,2),
            val_total NUMERIC(10,2),
            data_criacao VARCHAR(50)
        );
    '''))
    conn.execute(text('''
        CREATE TABLE IF NOT EXISTS orcamentos (
            id_orcamento SERIAL PRIMARY KEY,
            numero_orcamento VARCHAR(50) UNIQUE,
            cliente_nome VARCHAR(255),
            telefone VARCHAR(50),
            descricao TEXT,
            status VARCHAR(50),
            val_total NUMERIC(10,2),
            data_criacao VARCHAR(50)
        );
    '''))
    conn.execute(text('''
        CREATE TABLE IF NOT EXISTS itens_catalogo (
            id_item SERIAL PRIMARY KEY,
            tipo VARCHAR(50),
            descricao VARCHAR(255),
            preco_venda NUMERIC(10,2)
        );
    '''))

# ==============================================================================
# 4. AUTENTICAÇÃO E SEGURANÇA
# ==============================================================================
USUARIO_CORRETO = "admin"
HASH_SENHA_CORRETA = "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918" # admin123 por padrão

def verificar_senha(senha_digitada, hash_alvo):
    return hashlib.sha256(senha_digitada.encode()).hexdigest() == hash_alvo

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

# --- TELA DE LOGIN ---
if not st.session_state["autenticado"]:
    col_l1, col_l2, col_l3 = st.columns([1, 1.5, 1])
    with col_l2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(f'''
            <div style="text-align: center; background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(16px); padding: 30px; border-radius: 14px; border: 1px solid rgba(255, 255, 255, 0.12);">
                {logo_banner_html}
                <h2 style="color: #ff8c00; margin-top: 5px; margin-bottom: 0px;">MICRO FOX TI</h2>
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

# ==============================================================================
# 5. BARRA LATERAL (SIDEBAR)
# ==============================================================================
with st.sidebar:
    st.markdown(f'''
        <div style="text-align: center; margin-bottom: 15px;">
            {logo_banner_html}
            <h3 style="color: #ff8c00; margin: 0;">MICRO FOX TI</h3>
            <span style="font-size: 11px; color: #94a3b8;">Suporte & Infraestrutura</span>
        </div>
    ''', unsafe_allow_html=True)
    st.markdown("---")
    st.caption(f"🟢 **Banco Conectado:** {tipo_banco.upper()}")
    if st.button("🔴 Sair / Logout", use_container_width=True):
        st.session_state["autenticado"] = False
        st.rerun()

# ==============================================================================
# 6. NAVEGAÇÃO SUPERIOR (BOTÕES REATIVOS)
# ==============================================================================
if "menu_principal_nav" not in st.session_state:
    st.session_state["menu_principal_nav"] = "Dashboard"

def set_pagina(pagina):
    st.session_state["menu_principal_nav"] = pagina

botoes_nav = [
    ("Dashboard", "Dashboard"),
    ("NOVA O.S.", "Criar O.S."),
    ("BUSCAR O.S.", "Consultar O.S."),
    ("NOVO ORÇAMENTO", "Criar Orçamento"),
    ("BUSCAR ORÇAMENTOS", "Consultar Orçamento"),
    ("CLIENTES", "Clientes"),
    ("CATÁLOGO", "Catálogo")
]

cols = st.columns(len(botoes_nav))
for i, (rotulo, destino) in enumerate(botoes_nav):
    cols[i].button(
        rotulo,
        key=f"btn_header_{i}_{destino}",
        on_click=set_pagina,
        args=(destino,),
        use_container_width=True
    )

st.markdown("<hr style='border: 1px solid rgba(255, 255, 255, 0.1); margin-top: 10px; margin-bottom: 20px;'>", unsafe_allow_html=True)
menu_principal = st.session_state["menu_principal_nav"]

# ==============================================================================
# 7. MÓDULOS DO SISTEMA
# ==============================================================================

# --- DASHBOARD ---
if menu_principal == "Dashboard":
    st.subheader("📊 Painel Geral de Operações")
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

# --- CRIAR O.S. ---
elif menu_principal == "Criar O.S.":
    st.subheader("📋 Nova Ordem de Serviço")
    st.caption("Preencha os dados abaixo para gerar um novo atendimento/O.S.")
    
    with st.form("form_nova_os", clear_on_submit=True):
        col_c1, col_c2 = st.columns(2)
        cliente_nome = col_c1.text_input("Nome do Cliente *")
        cpf_cnpj = col_c2.text_input("CPF/CNPJ")
        
        col_c3, col_c4 = st.columns(2)
        telefone = col_c3.text_input("Telefone / WhatsApp *")
        email = col_c4.text_input("E-mail")
        
        st.markdown("---")
        col_eq1, col_eq2 = st.columns(2)
        equipamento = col_eq1.text_input("Equipamento / Dispositivo *", placeholder="Ex: Notebook Dell / Switch Cisco 2960")
        num_serie = col_eq2.text_input("Nº de Série / Tag")
        
        defeito_relatado = st.text_area("Defeito Relatado / Solicitação do Cliente *", placeholder="Descreva o problema detalhadamente...")
        observacoes = st.text_area("Observações Internas / Acessórios Deixados", placeholder="Ex: Fonte inclusa, cabo de força, etc.")
        
        col_v1, col_v2, col_v3 = st.columns(3)
        status_inicial = col_v1.selectbox("Status Inicial", ["Aberta", "Em Análise", "Aguardando Peça", "Aprovada"])
        val_servico = col_v2.number_input("Valor Serviços (R$)", min_value=0.0, step=10.0, format="%.2f")
        val_pecas = col_v3.number_input("Valor Peças (R$)", min_value=0.0, step=10.0, format="%.2f")
        
        val_total = val_servico + val_pecas
        st.markdown(f"### **Total da O.S.: R$ {val_total:,.2f}**")
        
        btn_salvar = st.form_submit_button("💾 GERAR ORDEM DE SERVIÇO", use_container_width=True)
        
        if btn_salvar:
            if not cliente_nome or not equipamento or not defeito_relatado:
                st.error("⚠️ Preencha os campos obrigatórios marcados com asterisco (*).")
            else:
                num_os = f"OS-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                data_abertura = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                try:
                    with engine.begin() as conn:
                        conn.execute(text('''
                            INSERT INTO clientes (nome, cpf_cnpj, telefone)
                            VALUES (:nome, :cpf, :tel)
                            ON CONFLICT DO NOTHING
                        '''), {"nome": cliente_nome, "cpf": cpf_cnpj, "tel": telefone})
                        
                        conn.execute(text('''
                            INSERT INTO ordens_servico 
                            (numero_os, cliente_nome, telefone, equipamento, num_serie, defeito_relatado, observacoes, status, val_servico, val_pecas, val_total, data_criacao)
                            VALUES (:num, :cli, :tel, :eq, :serie, :def, :obs, :st, :v_serv, :v_pec, :v_tot, :dt)
                        '''), {
                            "num": num_os, "cli": cliente_nome, "tel": telefone,
                            "eq": equipamento, "serie": num_serie, "def": defeito_relatado,
                            "obs": observacoes, "st": status_inicial, "v_serv": val_servico,
                            "v_pec": val_pecas, "v_tot": val_total, "dt": data_abertura
                        })
                    
                    st.success(f"✅ Ordem de Serviço **{num_os}** registrada com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao salvar O.S.: {e}")

# --- CONSULTAR O.S. ---
elif menu_principal == "Consultar O.S.":
    st.subheader("🔍 Consultar Ordens de Serviço")
    busca_termo = st.text_input("Buscar por Nome do Cliente, Equipamento ou Nº da O.S.")
    try:
        if busca_termo:
            query = text('''SELECT numero_os AS "Nº OS", cliente_nome AS "Cliente", telefone AS "Telefone", equipamento AS "Equipamento", status AS "Status", val_total AS "Total (R$)", data_criacao AS "Data" FROM ordens_servico WHERE cliente_nome ILIKE :b OR equipamento ILIKE :b OR numero_os ILIKE :b ORDER BY id_os DESC''')
            df_busca = pd.read_sql_query(query, engine, params={"b": f"%{busca_termo}%"})
        else:
            query = text('''SELECT numero_os AS "Nº OS", cliente_nome AS "Cliente", telefone AS "Telefone", equipamento AS "Equipamento", status AS "Status", val_total AS "Total (R$)", data_criacao AS "Data" FROM ordens_servico ORDER BY id_os DESC''')
            df_busca = pd.read_sql_query(query, engine)
        st.dataframe(df_busca, use_container_width=True)
    except Exception as e:
        st.info("Nenhum registro encontrado ou tabela não inicializada.")

# --- CRIAR ORÇAMENTO ---
elif menu_principal == "Criar Orçamento":
    st.subheader("📝 Novo Orçamento")
    with st.form("form_orcamento", clear_on_submit=True):
        c1, c2 = st.columns(2)
        cli_orc = c1.text_input("Nome do Cliente *")
        tel_orc = c2.text_input("Telefone *")
        desc_orc = st.text_area("Descrição do Serviço / Proposta *")
        val_orc = st.number_input("Valor Total Proposto (R$)", min_value=0.0, step=10.0, format="%.2f")
        
        if st.form_submit_button("💾 GERAR PROPOSTA DE ORÇAMENTO", use_container_width=True):
            if cli_orc and desc_orc:
                num_orc = f"ORC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                dt_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                try:
                    with engine.begin() as conn:
                        conn.execute(text('''
                            INSERT INTO orcamentos (numero_orcamento, cliente_nome, telefone, descricao, status, val_total, data_criacao)
                            VALUES (:num, :cli, :tel, :desc, 'Pendente', :val, :dt)
                        '''), {"num": num_orc, "cli": cli_orc, "tel": tel_orc, "desc": desc_orc, "val": val_orc, "dt": dt_now})
                    st.success(f"✅ Orçamento **{num_orc}** gerado com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao salvar orçamento: {e}")
            else:
                st.error("Preencha o cliente e a descrição da proposta.")

# --- CONSULTAR ORÇAMENTOS ---
elif menu_principal == "Consultar Orçamento":
    st.subheader("🔍 Consultar Orçamentos")
    try:
        df_orcs = pd.read_sql_query(text('''SELECT numero_orcamento AS "Nº Proposta", cliente_nome AS "Cliente", telefone AS "Telefone", status AS "Status", val_total AS "Total (R$)", data_criacao AS "Data" FROM orcamentos ORDER BY id_orcamento DESC'''), engine)
        st.dataframe(df_orcs, use_container_width=True)
    except Exception as e:
        st.info("Nenhum orçamento encontrado.")

# --- CLIENTES ---
elif menu_principal == "Clientes":
    st.subheader("👥 Base de Clientes")
    try:
        df_cli = pd.read_sql_query(text('''SELECT id_cliente AS "ID", nome AS "Nome", cpf_cnpj AS "CPF/CNPJ", telefone AS "Telefone", cidade AS "Cidade", uf AS "UF" FROM clientes ORDER BY nome ASC'''), engine)
        st.dataframe(df_cli, use_container_width=True)
    except Exception as e:
        st.info("Base de clientes vazia ou não inicializada.")

# --- CATÁLOGO ---
elif menu_principal == "Catálogo":
    st.subheader("📦 Catálogo de Produtos e Serviços")
    with st.form("form_cat"):
        c1, c2, c3 = st.columns([1, 2, 1])
        tipo = c1.selectbox("Tipo", ["Serviço", "Produto"])
        desc = c2.text_input("Descrição")
        preco = c3.number_input("Preço Venda (R$)", min_value=0.0, step=10.0, format="%.2f")
        if st.form_submit_button("Salvar no Catálogo"):
            if desc:
                try:
                    with engine.begin() as conn:
                        conn.execute(text("INSERT INTO itens_catalogo (tipo, descricao, preco_venda) VALUES (:t, :d, :p)"), {"t": tipo, "d": desc, "p": preco})
                    st.success("Item salvo no catálogo!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar no catálogo: {e}")

    try:
        df_cat = pd.read_sql_query(text('''SELECT id_item AS "ID", tipo AS "Tipo", descricao AS "Descrição", preco_venda AS "Preço (R$)" FROM itens_catalogo ORDER BY descricao ASC'''), engine)
        st.dataframe(df_cat, use_container_width=True)
    except Exception as e:
        st.info("Catálogo vazio ou não inicializado.")

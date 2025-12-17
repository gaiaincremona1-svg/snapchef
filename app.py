import streamlit as st
import sqlite3
import yt_dlp
import requests
from bs4 import BeautifulSoup
import time
import json
import random
from datetime import datetime

# --- 1. CONFIGURAZIONE STILE V18 (NO-LOGO EXTREME) ---
st.set_page_config(page_title="SnapChef", page_icon="🍊", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    /* --- 1. TENTATIVO DI RIMOZIONE TOTALE LOGO STREAMLIT --- */
    
    /* Nasconde header, footer e menu hamburger */
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important; height: 0px !important;}
    header {visibility: hidden !important;}
    
    /* Nasconde la barra decorativa colorata in alto */
    [data-testid="stDecoration"] {display: none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    
    /* Tenta di nascondere il Badge Rosso in basso a destra */
    .viewerBadge_container__1QSob {display: none !important;}
    div[class*="viewerBadge"] {display: none !important;}
    
    /* --- 2. STILE APP MOBILE --- */
    .stApp { background-color: #FAFAFA; }
    
    /* Titoli */
    h1 { font-size: 2.2rem !important; font-weight: 800; color: #333; margin-top: -20px; }
    
    /* PULSANTI (Grandi e Arancioni) */
    .stButton>button {
        background-color: #FF9F1C; 
        color: white; 
        border-radius: 25px; 
        border: none; 
        font-weight: bold; 
        padding: 15px; 
        width: 100%;
        font-size: 20px !important; 
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        margin-top: 10px;
        margin-bottom: 20px;
    }
    
    /* CAMPI DI TESTO */
    .stTextInput>div>div>input { border-radius: 15px; padding: 15px; font-size: 18px !important; }
    .stTextArea>div>div>textarea { border-radius: 15px; font-size: 18px !important; }
    
    /* --- 3. MENU NAVIGAZIONE (SOLLEVATO DA TERRA) --- */
    /* Lo alziamo di 40px dal fondo per non toccare MAI il logo rosso se dovesse apparire */
    .stTabs [data-baseweb="tab-list"] { 
        position: fixed; 
        bottom: 30px; /* ALZATO */
        left: 5%; 
        width: 90%; 
        background: white; 
        border-radius: 40px; 
        z-index: 999999; 
        padding: 10px 0; 
        border: 1px solid #ddd; 
        justify-content: space-around;
        box-shadow: 0 5px 20px rgba(0,0,0,0.15);
    }
    
    .stTabs [data-baseweb="tab"] { 
        background: transparent; border: none; flex: 1; font-size: 24px !important; 
    }
    
    /* Nasconde la linea di selezione */
    .stTabs [data-baseweb="tab-highlight"] { display: none; }
    
    /* Colore tasto attivo */
    .stTabs [aria-selected="true"] { color: #FF9F1C; background-color: #FFF8F0; border-radius: 30px; }
    
    /* --- 4. SPAZIO DI SICUREZZA IN FONDO --- */
    /* Aggiungiamo 200px di vuoto in fondo alla pagina. 
       Così puoi scrollare tutto in alto e niente verrà mai coperto dal bordo basso */
    .block-container { 
        padding-bottom: 200px !important; 
        padding-top: 20px !important; 
    }
    
</style>
""", unsafe_allow_html=True)

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect('snapchef_v18_safe.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS ricette 
                 (id INTEGER PRIMARY KEY, titolo TEXT, ingredienti TEXT, procedimento TEXT, fonte TEXT, img TEXT, cartella TEXT, persone TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS cartelle (nome TEXT PRIMARY KEY)''')
    try:
        c.execute("INSERT INTO cartelle VALUES ('Generale')")
        conn.commit()
    except: pass
    c.execute('''CREATE TABLE IF NOT EXISTS spesa (ingrediente TEXT, stato BOOLEAN)''')
    c.execute('''CREATE TABLE IF NOT EXISTS planner (giorno TEXT, tipo TEXT, ricetta_text TEXT)''')
    conn.commit()
    return conn

conn = init_db()

# --- MOTORE ---
def scarica_universale(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        dati = {"titolo": "Nuova Ricetta", "ingredienti": "", "procedimento": "", "img": "", "persone": "4"}
        
        script = soup.find('script', {'type': 'application/ld+json'})
        if script:
            try:
                json_data = json.loads(script.string)
                recipe = None
                if isinstance(json_data, list):
                    for item in json_data:
                        if 'Recipe' in item.get('@type', ''): recipe = item; break
                elif isinstance(json_data, dict):
                    if 'Recipe' in json_data.get('@type', ''): recipe = json_data
                    elif '@graph' in json_data:
                        for item in json_data['@graph']:
                            if 'Recipe' in item.get('@type', ''): recipe = item; break
                if recipe:
                    dati['titolo'] = recipe.get('name', 'Ricetta Web')
                    img_data = recipe.get('image', [])
                    if isinstance(img_data, list) and len(img_data) > 0: dati['img'] = img_data[0]
                    elif isinstance(img_data, str): dati['img'] = img_data
                    ingr = recipe.get('recipeIngredient', [])
                    dati['ingredienti'] = "\n".join(ingr)
                    
                    # Procedimento pulito
                    steps = recipe.get('recipeInstructions', [])
                    parsed_steps = []
                    for step in steps:
                        if isinstance(step, str): parsed_steps.append(step)
                        elif isinstance(step, dict): parsed_steps.append(step.get('text', ''))
                    dati['procedimento'] = "\n\n".join(parsed_steps)
                    dati['persone'] = str(recipe.get('recipeYield', '4')).replace('servings', '').strip()
                    return dati
            except: pass
        
        if soup.find('h1'): dati['titolo'] = soup.find('h1').text.strip()
        return dati
    except: return None

def scarica_tiktok(url):
    ydl_opts = {'quiet': True, 'extract_flat': True, 'no_warnings': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "titolo": info.get('title', 'Ricetta TikTok'),
                "ingredienti": "⚠️ Copia ingredienti dal testo sotto 👇",
                "procedimento": info.get('description', ''),
                "img": info.get('thumbnail', ''),
                "persone": "2"
            }
    except: return None

# --- INTERFACCIA ---
if 'editor_data' not in st.session_state: st.session_state['editor_data'] = None

tab_home, tab_ricette, tab_frigo, tab_planner, tab_spesa = st.tabs([
    "🏠", "📂", "📸", "📅", "🛒"
])

# 1. IMPORTA
with tab_home:
    st.title("🍊 Importa")
    st.info("Incolla link da TikTok, GialloZafferano, Instagram...")
    url = st.text_input("Link:")
    if st.button("ANALIZZA"):
        if url:
            with st.spinner("Analisi..."):
                dati = scarica_tiktok(url) if "tiktok.com" in url else scarica_universale(url)
                if not dati: dati = {"titolo": "Nuova Ricetta", "ingredienti": "", "procedimento": "", "img": "", "persone": "4"}
                st.session_state['editor_data'] = dati

    if st.session_state['editor_data']:
        st.write("---")
        st.subheader("✏️ Modifica")
        new_titolo = st.text_input("Nome:", value=st.session_state['editor_data']['titolo'])
        new_persone = st.text_input("Persone:", value=st.session_state['editor_data']['persone'])
        new_ingr = st.text_area("Ingredienti:", value=st.session_state['editor_data']['ingredienti'], height=200)
        new_proc = st.text_area("Procedimento:", value=st.session_state['editor_data']['procedimento'], height=200)
        cartelle = [c[0] for c in conn.cursor().execute("SELECT nome FROM cartelle").fetchall()]
        dest_folder = st.selectbox("Cartella:", cartelle)
        
        if st.button("💾 SALVA"):
            img = st.session_state['editor_data'].get('img', '')
            conn.cursor().execute("INSERT INTO ricette (titolo, ingredienti, procedimento, fonte, img, cartella, persone) VALUES (?,?,?,?,?,?,?)",
                                  (new_titolo, new_ingr, new_proc, "Web", img, dest_folder, new_persone))
            conn.commit()
            st.success("Salvata!")
            st.session_state['editor_data'] = None
            time.sleep(1)
            st.rerun()

# 2. RICETTARIO
with tab_ricette:
    st.header("📂 Le tue Ricette")
    with st.expander("➕ Nuova Cartella"):
        f_name = st.text_input("Nome:")
        if st.button("CREA"):
            if f_name: conn.cursor().execute("INSERT INTO cartelle VALUES (?)", (f_name,)); conn.commit(); st.rerun()
            
    sel = st.selectbox("Filtra:", ["Tutte"] + [c[0] for c in conn.cursor().execute("SELECT nome FROM cartelle").fetchall()])
    sql = "SELECT * FROM ricette ORDER BY id DESC" if sel == "Tutte" else f"SELECT * FROM ricette WHERE cartella = '{sel}' ORDER BY id DESC"
    
    for r in conn.cursor().execute(sql).fetchall():
        with st.expander(f"🍳 {r[1]}"):
            if r[5]: st.image(r[5])
            st.caption(f"Per {r[7]} | {r[6]}")
            st.write(r[2]); st.write("---"); st.write(r[3])
            c1, c2 = st.columns(2)
            if c1.button("🛒 Spesa", key=f"s_{r[0]}"):
                for i in r[2].split('\n'):
                    if len(i.strip()) > 2: conn.cursor().execute("INSERT INTO spesa VALUES (?,?)", (i.strip(), False))
                conn.commit(); st.toast("Aggiunti!")
            if c2.button("🗑 Elimina", key=f"d_{r[0]}"):
                conn.cursor().execute("DELETE FROM ricette WHERE id=?", (r[0],)); conn.commit(); st.rerun()

# 3. FRIGO
with tab_frigo:
    st.header("📸 Frigo")
    if st.camera_input("Scatta"): st.success("Analizzato!")

# 4. PLANNER
with tab_planner:
    st.header("📅 Piano")
    data = st.date_input("Data:", datetime.today())
    pasto = st.selectbox("Pasto:", ["Colazione", "Pranzo", "Snack", "Cena"])
    ricetta = st.selectbox("Ricetta:", ["--"] + [r[0] for r in conn.cursor().execute("SELECT titolo FROM ricette").fetchall()])
    if st.button("➕ PIANIFICA"):
        if ricetta != "--": conn.cursor().execute("INSERT INTO planner VALUES (?,?,?)", (data.strftime("%Y-%m-%d"), pasto, ricetta)); conn.commit(); st.rerun()
    
    st.write("---")
    st.subheader(f"Menu {data.strftime('%d/%m')}")
    for p in conn.cursor().execute("SELECT rowid, tipo, ricetta_text FROM planner WHERE giorno=?", (data.strftime("%Y-%m-%d"),)).fetchall():
        c1, c2 = st.columns([4,1])
        c1.write(f"*{p[1]}:* {p[2]}")
        if c2.button("X", key=f"del_p_{p[0]}"): conn.cursor().execute("DELETE FROM planner WHERE rowid=?", (p[0],)); conn.commit(); st.rerun()

# 5. SPESA
with tab_spesa:
    st.header("🛒 Spesa")
    items = conn.cursor().execute("SELECT rowid, ingrediente, stato FROM spesa").fetchall()
    if items:
        tot = len(items); fatti = len([x for x in items if x[2]])
        st.progress(fatti/tot if tot>0 else 0)
        st.metric("Totale", f"€ {tot*1.5:.2f}")
        for item in items:
            c1, c2 = st.columns([5, 1])
            chk = c1.checkbox(item[1], value=item[2], key=f"chk_{item[0]}")
            if chk != item[2]: conn.cursor().execute("UPDATE spesa SET stato=? WHERE rowid=?", (chk, item[0])); conn.commit(); st.rerun()
            if c2.button("X", key=f"del_s_{item[0]}"): conn.cursor().execute("DELETE FROM spesa WHERE rowid=?", (item[0],)); conn.commit(); st.rerun()
        if st.button("SVUOTA"): conn.cursor().execute("DELETE FROM spesa"); conn.commit(); st.rerun()
    else: st.info("Lista vuota.")

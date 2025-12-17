import streamlit as st
import sqlite3
import yt_dlp
import requests
from bs4 import BeautifulSoup
import time
import json
import random
from datetime import datetime

# --- 1. CONFIGURAZIONE STILE V17 (INVISIBLE MODE) ---
st.set_page_config(page_title="SnapChef", page_icon="🍊", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    /* --- 1. NASCONDI TUTTO IL BRANDING STREAMLIT --- */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Nasconde la barra rossa in basso a destra */
    div[class^="viewerBadge"] {display: none !important;}
    .viewerBadge_container__1QSob {display: none !important;}
    .stDeployButton {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    
    /* --- 2. MIGLIORA I TASTI E IL TESTO --- */
    .stApp { background-color: #FAFAFA; }
    
    /* Titoli più grandi */
    h1 { font-size: 2.5rem !important; font-weight: 800 !important; color: #333; }
    h2, h3 { font-size: 1.8rem !important; }
    p, div { font-size: 18px !important; } /* Testo normale più leggibile */
    
    /* PULSANTONI GRANDI (Arancioni) */
    .stButton>button {
        background-color: #FF9F1C; 
        color: white; 
        border-radius: 25px; 
        border: none; 
        font-weight: bold; 
        padding: 20px 10px; /* Più alti */
        width: 100%;
        font-size: 22px !important; /* Scritta gigante */
        box-shadow: 0 4px 15px rgba(255, 159, 28, 0.4);
        margin-top: 15px;
        margin-bottom: 15px;
    }
    .stButton>button:active { transform: scale(0.98); background-color: #E0890E; }
    
    /* CAMPI DI TESTO COMODI */
    .stTextInput>div>div>input { 
        border-radius: 15px; 
        padding: 15px; 
        font-size: 20px !important; 
        min-height: 60px;
    }
    .stTextArea>div>div>textarea { border-radius: 15px; font-size: 18px !important; }
    
    /* --- 3. MENU DI NAVIGAZIONE IN BASSO (PERFETTO) --- */
    .stTabs [data-baseweb="tab-list"] { 
        position: fixed; 
        bottom: 20px; /* STACCATO dal fondo per evitare bordi del telefono */
        left: 2%; 
        width: 96%; /* Leggermente più stretto per sembrare una "pillola" */
        background: white; 
        border-radius: 50px; /* Arrotondato */
        z-index: 999999; /* Sopra a tutto! */
        padding: 10px 5px; 
        border: 1px solid #eee; 
        justify-content: space-around;
        box-shadow: 0 10px 30px rgba(0,0,0,0.15);
    }
    
    /* Tasti del menu */
    .stTabs [data-baseweb="tab"] { 
        background: transparent; 
        border: none; 
        flex: 1; 
        font-size: 28px !important; /* Icone giganti */
        padding: 5px 0;
        height: auto;
    }
    
    /* Nasconde la linea di selezione standard brutta */
    .stTabs [data-baseweb="tab-highlight"] { display: none; }
    
    /* Quando selezioni un tasto */
    .stTabs [aria-selected="true"] { 
        color: #FF9F1C; 
        background-color: #FFF4E6;
        border-radius: 30px;
    }
    
    /* Spazio extra in fondo per non coprire il contenuto */
    .block-container { padding-bottom: 180px !important; padding-top: 20px !important; }
    
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
def init_db():
    conn = sqlite3.connect('snapchef_v17_mobile.db', check_same_thread=False)
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

# --- 3. MOTORE ---
def scarica_universale(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
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
        ingr_list = []
        for tag in soup.find_all(['li', 'div', 'p']):
            txt = tag.text.strip()
            if any(x in txt.lower() for x in ['gr', 'ml', 'kg', 'q.b', 'cucchiai']) and len(txt) < 80:
                ingr_list.append(txt)
        dati['ingredienti'] = "\n".join(list(set(ingr_list)))
        return dati
    except: return None

def scarica_tiktok(url):
    ydl_opts = {'quiet': True, 'extract_flat': True, 'no_warnings': True, 'ignoreerrors': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            titolo = info.get('title', 'Ricetta TikTok')
            desc = info.get('description', '')
            img = info.get('thumbnail', '')
            return {"titolo": titolo, "ingredienti": "⚠️ Copia ingredienti dal testo sotto 👇", "procedimento": desc, "img": img, "persone": "2"}
    except: return None

# --- 4. INTERFACCIA ---
if 'editor_data' not in st.session_state: st.session_state['editor_data'] = None

# MENU CON ICONE GRANDI
tab_home, tab_ricette, tab_frigo, tab_planner, tab_spesa = st.tabs([
    "🏠 Home", "📂 Ricette", "📸 Frigo", "📅 Piano", "🛒 Spesa"
])

# 1. IMPORTA
with tab_home:
    st.title("🍊 Importa")
    url = st.text_input("Link Ricetta:")
    if st.button("ANALIZZA LINK"):
        if url:
            with st.spinner("Analisi in corso..."):
                dati = scarica_tiktok(url) if "tiktok.com" in url else scarica_universale(url)
                if not dati: dati = {"titolo": "Nuova Ricetta", "ingredienti": "", "procedimento": "", "img": "", "persone": "4"}
                st.session_state['editor_data'] = dati

    if st.session_state['editor_data']:
        st.write("---")
        st.subheader("✏️ Editor")
        new_titolo = st.text_input("Nome:", value=st.session_state['editor_data']['titolo'])
        new_persone = st.text_input("Persone:", value=st.session_state['editor_data']['persone'])
        new_ingr = st.text_area("Ingredienti:", value=st.session_state['editor_data']['ingredienti'], height=200)
        new_proc = st.text_area("Procedimento:", value=st.session_state['editor_data']['procedimento'], height=200)
        cartelle = [c[0] for c in conn.cursor().execute("SELECT nome FROM cartelle").fetchall()]
        dest_folder = st.selectbox("Cartella:", cartelle)
        
        if st.button("💾 SALVA RICETTA"):
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
    with st.expander("➕ Crea Nuova Cartella"):
        f_name = st.text_input("Nome Cartella:")
        if st.button("CREA"):
            if f_name: conn.cursor().execute("INSERT INTO cartelle VALUES (?)", (f_name,)); conn.commit(); st.rerun()
            
    sel = st.selectbox("Filtra Cartella:", ["Tutte"] + [c[0] for c in conn.cursor().execute("SELECT nome FROM cartelle").fetchall()])
    sql = "SELECT * FROM ricette ORDER BY id DESC" if sel == "Tutte" else f"SELECT * FROM ricette WHERE cartella = '{sel}' ORDER BY id DESC"
    
    for r in conn.cursor().execute(sql).fetchall():
        with st.expander(f"🍳 {r[1]}"):
            if r[5]: st.image(r[5])
            st.caption(f"Per {r[7]} | {r[6]}")
            st.write(r[2]); st.write("---"); st.write(r[3])
            c1, c2 = st.columns(2)
            if c1.button("🛒 Metti in Spesa", key=f"s_{r[0]}"):
                for i in r[2].split('\n'):
                    if len(i.strip()) > 2: conn.cursor().execute("INSERT INTO spesa VALUES (?,?)", (i.strip(), False))
                conn.commit(); st.toast("Ingredienti aggiunti!")
            if c2.button("🗑 Elimina", key=f"d_{r[0]}"):
                conn.cursor().execute("DELETE FROM ricette WHERE id=?", (r[0],)); conn.commit(); st.rerun()

# 3. FRIGO
with tab_frigo:
    st.header("📸 Frigo Magic")
    if st.camera_input("Scatta Foto"): st.success("Foto caricata! L'AI sta analizzando...")

# 4. PLANNER
with tab_planner:
    st.header("📅 Calendario")
    data = st.date_input("Scegli Data:", datetime.today())
    pasto = st.selectbox("Scegli Pasto:", ["Colazione", "Pranzo", "Snack", "Cena"])
    ricetta = st.selectbox("Scegli Ricetta:", ["--"] + [r[0] for r in conn.cursor().execute("SELECT titolo FROM ricette").fetchall()])
    if st.button("➕ AGGIUNGI AL PIANO"):
        if ricetta != "--": conn.cursor().execute("INSERT INTO planner VALUES (?,?,?)", (data.strftime("%Y-%m-%d"), pasto, ricetta)); conn.commit(); st.rerun()
    
    st.write("---")
    st.subheader(f"Menu del {data.strftime('%d/%m')}")
    for p in conn.cursor().execute("SELECT rowid, tipo, ricetta_text FROM planner WHERE giorno=?", (data.strftime("%Y-%m-%d"),)).fetchall():
        c1, c2 = st.columns([4,1])
        c1.write(f"*{p[1]}:* {p[2]}")
        if c2.button("X", key=f"del_p_{p[0]}"): conn.cursor().execute("DELETE FROM planner WHERE rowid=?", (p[0],)); conn.commit(); st.rerun()

# 5. SPESA
with tab_spesa:
    st.header("🛒 Lista Spesa")
    items = conn.cursor().execute("SELECT rowid, ingrediente, stato FROM spesa").fetchall()
    if items:
        tot = len(items); fatti = len([x for x in items if x[2]])
        st.progress(fatti/tot if tot>0 else 0)
        st.metric("Totale Stimato", f"€ {tot*1.5:.2f}")
        for item in items:
            c1, c2 = st.columns([5, 1])
            chk = c1.checkbox(item[1], value=item[2], key=f"chk_{item[0]}")
            if chk != item[2]: conn.cursor().execute("UPDATE spesa SET stato=? WHERE rowid=?", (chk, item[0])); conn.commit(); st.rerun()
            if c2.button("X", key=f"del_s_{item[0]}"): conn.cursor().execute("DELETE FROM spesa WHERE rowid=?", (item[0],)); conn.commit(); st.rerun()
        if st.button("SVUOTA LISTA"): conn.cursor().execute("DELETE FROM spesa"); conn.commit(); st.rerun()
    else: st.info("La lista è vuota.")

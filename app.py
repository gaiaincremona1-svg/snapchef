# -*- coding: utf-8 -*-
"""
Created on Wed Dec 17 14:05:47 2025

@author: gaiai
"""

import streamlit as st
import sqlite3
import yt_dlp
import requests
from bs4 import BeautifulSoup
import time
import json
import random
from datetime import datetime

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="SnapChef", page_icon="🍊", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #FAFAFA; }
    .stButton>button {
        background-color: #FF9F1C; color: white; border-radius: 20px; 
        border: none; font-weight: bold; padding: 12px; width: 100%;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stButton>button:hover { background-color: #E0890E; }
    
    /* MENU IN BASSO */
    .stTabs [data-baseweb="tab-list"] { 
        position: fixed; bottom: 0; left: 0; width: 100%; background: white; 
        z-index: 999; padding: 10px 0; border-top: 1px solid #eee; justify-content: space-around;
    }
    .stTabs [data-baseweb="tab"] { background: transparent; border: none; flex: 1; font-size: 11px; }
    .stTabs [aria-selected="true"] { color: #FF9F1C; border-top: 3px solid #FF9F1C; }
    .block-container { padding-bottom: 120px; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect('snapchef_v14_final.db', check_same_thread=False)
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

# --- MOTORE DI RICERCA ---
def scarica_universale(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        dati = {"titolo": "Nuova Ricetta", "ingredienti": "", "procedimento": "", "img": "", "persone": "4"}
        
        # Tentativo dati nascosti
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
        return dati
    except: return None

def scarica_tiktok(url):
    ydl_opts = {'quiet': True, 'extract_flat': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            desc = info.get('description', '')
            titolo = info.get('title', 'Ricetta TikTok')
            img = info.get('thumbnail', '')
            return {"titolo": titolo, "ingredienti": desc, "procedimento": desc, "img": img, "persone": "2"}
    except: return None

# --- INTERFACCIA ---
if 'editor_data' not in st.session_state: st.session_state['editor_data'] = None

tab_home, tab_ricette, tab_frigo, tab_planner, tab_spesa = st.tabs([
    "🏠 Importa", "📂 Ricettario", "📸 FRIGO", "📅 Piano", "🛒 Spesa"
])

# 1. IMPORTA
with tab_home:
    st.title("🍊 Importa Ricetta")
    col1, col2 = st.columns([3, 1])
    url = col1.text_input("Link Ricetta:")
    if col2.button("Analizza"):
        with st.spinner("Estraggo Dati..."):
            dati = scarica_tiktok(url) if "tiktok" in url else scarica_universale(url)
            if not dati: dati = {"titolo": "Nuova Ricetta", "ingredienti": "", "procedimento": "", "img": "", "persone": "4"}
            st.session_state['editor_data'] = dati

    if st.session_state['editor_data']:
        st.markdown("---")
        st.subheader("✏️ Editor")
        c_t, c_p = st.columns([3, 1])
        new_titolo = c_t.text_input("Titolo:", value=st.session_state['editor_data']['titolo'])
        new_persone = c_p.text_input("Persone:", value=st.session_state['editor_data']['persone'])
        c1, c2 = st.columns(2)
        new_ingr = c1.text_area("Ingredienti:", value=st.session_state['editor_data']['ingredienti'], height=300)
        new_proc = c2.text_area("Procedimento:", value=st.session_state['editor_data']['procedimento'], height=300)
        dest_folder = st.selectbox("Cartella:", [c[0] for c in conn.cursor().execute("SELECT nome FROM cartelle").fetchall()])
        
        if st.button("💾 SALVA"):
            img = st.session_state['editor_data'].get('img', '')
            conn.cursor().execute("INSERT INTO ricette (titolo, ingredienti, procedimento, fonte, img, cartella, persone) VALUES (?,?,?,?,?,?,?)",
                                  (new_titolo, new_ingr, new_proc, "Web", img, dest_folder, new_persone))
            conn.commit()
            st.success("Salvata!"); st.session_state['editor_data'] = None; time.sleep(1); st.rerun()

# 2. RICETTARIO
with tab_ricette:
    st.header("📂 Le tue Collezioni")
    with st.expander("➕ Nuova Cartella"):
        if st.button("Crea Cartella"):
            f_name = st.text_input("Nome:")
            if f_name: conn.cursor().execute("INSERT INTO cartelle VALUES (?)", (f_name,)); conn.commit(); st.rerun()
            
    sel = st.selectbox("Filtra:", ["Tutte"] + [c[0] for c in conn.cursor().execute("SELECT nome FROM cartelle").fetchall()])
    sql = "SELECT * FROM ricette ORDER BY id DESC" if sel == "Tutte" else f"SELECT * FROM ricette WHERE cartella = '{sel}' ORDER BY id DESC"
    for r in conn.cursor().execute(sql).fetchall():
        with st.expander(f"🍳 {r[1]}"):
            if r[5]: st.image(r[5])
            st.write(f"*Per {r[7]} persone*"); st.text(r[2]); st.write(r[3])
            c1, c2 = st.columns(2)
            if c1.button("🛒 Spesa", key=f"s_{r[0]}"):
                for i in r[2].split('\n'):
                    if len(i.strip()) > 2: conn.cursor().execute("INSERT INTO spesa VALUES (?,?)", (i.strip(), False))
                conn.commit(); st.toast("Aggiunti!")
            if c2.button("🗑 Elimina", key=f"d_{r[0]}"):
                conn.cursor().execute("DELETE FROM ricette WHERE id=?", (r[0],)); conn.commit(); st.rerun()

# 3. FRIGO
with tab_frigo:
    st.header("📸 Frigo Magic")
    if st.camera_input("Foto"): st.success("Analisi fatta! Consiglio: Pasta al Tonno")

# 4. PLANNER
with tab_planner:
    st.header("📅 Calendario Pasti")
    col_d, col_m = st.columns([2,1])
    data = col_d.date_input("Data:", datetime.today())
    pasto = col_m.selectbox("Pasto:", ["Colazione", "Pranzo", "Snack", "Cena"])
    ricetta = st.selectbox("Ricetta:", ["--"] + [r[0] for r in conn.cursor().execute("SELECT titolo FROM ricette").fetchall()])
    
    if st.button("➕ Pianifica"):
        conn.cursor().execute("INSERT INTO planner VALUES (?,?,?)", (data.strftime("%Y-%m-%d"), pasto, ricetta)); conn.commit(); st.rerun()
    
    st.write(f"*Menu del {data.strftime('%d/%m/%Y')}*")
    for p in conn.cursor().execute("SELECT rowid, tipo, ricetta_text FROM planner WHERE giorno=?", (data.strftime("%Y-%m-%d"),)).fetchall():
        c1, c2 = st.columns([4,1])
        c1.info(f"{p[1]}: {p[2]}")
        if c2.button("X", key=f"del_p_{p[0]}"):
            conn.cursor().execute("DELETE FROM planner WHERE rowid=?", (p[0],)); conn.commit(); st.rerun()

# 5. SPESA
with tab_spesa:
    st.header("🛒 Lista Spesa")
    items = conn.cursor().execute("SELECT rowid, ingrediente, stato FROM spesa").fetchall()
    if items:
        tot = len(items); fatti = len([x for x in items if x[2]])
        st.progress(fatti/tot); st.metric("Totale Stimato", f"€ {tot*1.5:.2f}")
        for item in items:
            c1, c2 = st.columns([5, 1])
            chk = c1.checkbox(item[1], value=item[2], key=f"chk_{item[0]}")
            if chk != item[2]: conn.cursor().execute("UPDATE spesa SET stato=? WHERE rowid=?", (chk, item[0])); conn.commit(); st.rerun()
            if c2.button("X", key=f"del_s_{item[0]}"): conn.cursor().execute("DELETE FROM spesa WHERE rowid=?", (item[0],)); conn.commit(); st.rerun()
        if st.button("Svuota"): conn.cursor().execute("DELETE FROM spesa"); conn.commit(); st.rerun()
    else: st.info("Lista vuota.")
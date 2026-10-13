import streamlit as st
import os
import json
import pandas as pd
from PIL import Image
import colorgram

st.set_page_config(page_title="Prism - Galerie d'Art", layout="wide")

# --- STYLE VISUEL ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .color-palette { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 15px; margin-bottom: 20px; }
    .color-box { width: 45px; height: 45px; border-radius: 8px; border: 1px solid #ffffff33; box-shadow: 0 4px 6px rgba(0,0,0,0.5); }
    div[data-testid="stDialog"] img {
        max-height: 85vh !important;
        width: auto !important;
        object-fit: contain !important;
        margin-bottom: 10px;
    }
    div[data-testid="stDialog"] [data-testid="stVerticalBlock"] { gap: 0.5rem; }
    .badge-mouvement { display: inline-block; padding: 2px 8px; background-color: #ffffff22; border-radius: 12px; font-size: 0.8em; margin-bottom: 5px;}
    </style>
    """, unsafe_allow_html=True)

st.title("🖼️ Prism : Galerie d'Art")

# --- CHEMINS DES FICHIERS ---
IMAGE_DIR = r"F:\Prism_Art\Ref_Images"
CACHE_FILE = r"F:\Prism_Art\palettes.json"
CATALOGUE_PATH = r"F:\Prism_Art\catalogue.csv"

# --- MÉMOIRE DES COULEURS (JSON) ---
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_cache(cache_data):
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, indent=4, ensure_ascii=False)

if 'memoire_couleurs' not in st.session_state:
    st.session_state.memoire_couleurs = load_cache()

def extract_colors(image_path, num_colors=8): 
    try:
        colors = colorgram.extract(image_path, num_colors) 
        palette_enrichie = []
        
        for c in colors:
            hex_code = f"#{c.rgb.r:02x}{c.rgb.g:02x}{c.rgb.b:02x}"
            pourcentage = round(c.proportion * 100, 1)
            
            h_std = int((c.hsl.h / 255) * 360)
            s_std = int((c.hsl.s / 255) * 100)
            l_std = int((c.hsl.l / 255) * 100)
            
            palette_enrichie.append({
                "hex": hex_code, 
                "percent": pourcentage,
                "h": h_std,
                "s": s_std,
                "l": l_std
            })
            
        return palette_enrichie
    except:
        return []

# --- LECTURE DU CATALOGUE (CSV) ---
def load_metadata():
    if os.path.exists(CATALOGUE_PATH):
        try:
            df = pd.read_csv(CATALOGUE_PATH, sep=";", encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(CATALOGUE_PATH, sep=";", encoding="latin1")
        df['Fichier'] = df['Fichier'].str.strip()
        return df
    return None

df_metadata = load_metadata()

def parse_filename(filename):
    name_clean = os.path.splitext(filename)[0].replace('_', ' ')
    parts = [p.strip() for p in name_clean.split(' -- ') if p.strip()]
    
    infos = {
        "artiste": parts[0] if len(parts) > 0 else "Inconnu",
        "titre": parts[1] if len(parts) > 1 else "Sans Titre",
        "annee": parts[2] if len(parts) > 2 else "Inconnue",
        "mouvement": "Non classé",
        "musee": "Non renseigné",
        "ville": "Non renseigné", # <-- NOUVEAU
        "pays": "Non renseigné"
    }

    if df_metadata is not None:
        ligne = df_metadata[df_metadata['Fichier'] == filename]
        if not ligne.empty:
            mouv = str(ligne.iloc[0]['Mouvement'])
            mus = str(ligne.iloc[0]['Musee'])
            
            # Utilisation de .get pour éviter un crash si la colonne manque au début
            vil = str(ligne.iloc[0].get('Ville', 'nan')) # <-- NOUVEAU
            pay = str(ligne.iloc[0]['Pays'])
            
            if mouv != 'nan' and mouv.strip(): infos["mouvement"] = mouv.strip()
            if mus != 'nan' and mus.strip(): infos["musee"] = mus.strip()
            if vil != 'nan' and vil.strip(): infos["ville"] = vil.strip() # <-- NOUVEAU
            if pay != 'nan' and pay.strip(): infos["pays"] = pay.strip()
            
    return infos

# --- PRÉPARATION DES DONNÉES POUR LES FILTRES ---
all_files = []
if os.path.exists(IMAGE_DIR):
    all_files = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.webp', '.png'))]

set_mouvements = set()
set_musees = set()
set_villes = set() # <-- NOUVEAU
set_pays = set()

for f in all_files:
    infos = parse_filename(f)
    if infos["mouvement"] != "Non classé": set_mouvements.add(infos["mouvement"])
    if infos["musee"] != "Non renseigné": set_musees.add(infos["musee"])
    if infos["ville"] != "Non renseigné": set_villes.add(infos["ville"]) # <-- NOUVEAU
    if infos["pays"] != "Non renseigné": set_pays.add(infos["pays"])

liste_mouvements = ["Tous"] + sorted(list(set_mouvements))
liste_musees = ["Tous"] + sorted(list(set_musees))
liste_villes = ["Tous"] + sorted(list(set_villes)) # <-- NOUVEAU
liste_pays = ["Tous"] + sorted(list(set_pays))

# --- BARRE LATÉRALE ---
st.sidebar.header("🔍 Recherche & Filtres")
search_query = st.sidebar.text_input("Mots-clés...", "")

selected_mouvement = st.sidebar.selectbox("Mouvement artistique", liste_mouvements)
selected_musee = st.sidebar.selectbox("Musée", liste_musees)
selected_ville = st.sidebar.selectbox("Ville", liste_villes) # <-- NOUVEAU
selected_pays = st.sidebar.selectbox("Pays", liste_pays)

st.sidebar.divider()
st.sidebar.header("⚙️ Paramètres")
col_count = st.sidebar.slider("Nombre de colonnes", 2, 6, 4)

# --- FENÊTRE POP-UP D'EXAMEN ---
@st.dialog("Examen de l'œuvre", width="large")
def afficher_analyse(filename, infos, path):
    col_visuel, col_details = st.columns([3, 1])
    
    with col_visuel:
        st.image(Image.open(path), use_container_width=True)
        
    with col_details:
        st.subheader(infos["titre"])
        
        if infos["mouvement"] != "Non classé":
            st.markdown(f'<span class="badge-mouvement">{infos["mouvement"]}</span>', unsafe_allow_html=True)
            
        st.write(f"**Artiste :** {infos['artiste']}")
        st.write(f"**Année :** {infos['annee']}")
        
        # Un affichage conditionnel propre pour la localisation
        if infos["musee"] != "Non renseigné":
            lieu_texte = f"**Lieu :** {infos['musee']}"
            if infos["ville"] != "Non renseigné":
                lieu_texte += f", {infos['ville']}"
            if infos["pays"] != "Non renseigné":
                lieu_texte += f" ({infos['pays']})"
            st.write(lieu_texte) # <-- NOUVEAU FORMATAGE
            
        st.divider()
        st.write("### 🎨 Palette")
        
        palette = []
        if filename in st.session_state.memoire_couleurs:
            palette = st.session_state.memoire_couleurs[filename]
        else:
            with st.spinner("Analyse..."):
                palette = extract_colors(path, 8)
                if palette:
                    st.session_state.memoire_couleurs[filename] = palette
                    save_cache(st.session_state.memoire_couleurs)
                    
        if palette:
            html_colors = ""
            for item in palette:
                c_hex = item["hex"]
                c_per = item["percent"]
                
                c_h = item.get("h", 0)
                c_s = item.get("s", 0)
                c_l = item.get("l", 0)
                
                info_bulle = f"{c_hex} | HSL({c_h}, {c_s}%, {c_l}%) | {c_per}% de l'œuvre"
                
                html_colors += (
                    f'<div style="display: flex; flex-direction: column; align-items: center;">'
                    f'<div class="color-box" style="background-color: {c_hex};" title="{info_bulle}"></div>'
                    f'<span style="font-size: 0.8em; margin-top: 4px; opacity: 0.8;">{c_per}%</span>'
                    f'</div>'
                )
            st.markdown(f'<div class="color-palette">{html_colors}</div>', unsafe_allow_html=True)

# --- AFFICHAGE DE LA GALERIE ---
if all_files:
    files_to_display = []
    
    for f in all_files:
        infos = parse_filename(f)
        
        # On inclut la ville dans la recherche globale par mots-clés
        texte_cache = f"{infos['artiste']} {infos['titre']} {infos['annee']} {infos['mouvement']} {infos['musee']} {infos['ville']} {infos['pays']}".lower()
        match_texte = search_query.lower() in texte_cache if search_query else True
        
        match_mouv = (selected_mouvement == "Tous") or (infos["mouvement"] == selected_mouvement)
        match_mus = (selected_musee == "Tous") or (infos["musee"] == selected_musee)
        match_ville = (selected_ville == "Tous") or (infos["ville"] == selected_ville) # <-- NOUVEAU
        match_pays = (selected_pays == "Tous") or (infos["pays"] == selected_pays)

        if match_texte and match_mouv and match_mus and match_ville and match_pays: # <-- NOUVEAU
            files_to_display.append((f, infos))
    
    if files_to_display:
        cols = st.columns(col_count)
        for index, (filename, infos) in enumerate(files_to_display):
            path = os.path.join(IMAGE_DIR, filename)
            with cols[index % col_count]:
                st.image(Image.open(path), use_container_width=True)
                st.markdown(f"**{infos['titre']}**")
                
                caption_text = f"{infos['artiste']} • {infos['annee']}"
                if infos["mouvement"] != "Non classé":
                    caption_text += f" • {infos['mouvement']}"
                st.caption(caption_text)
                
                if st.button("🔍 Examiner", key=f"btn_{filename}", use_container_width=True):
                    afficher_analyse(filename, infos, path)
    else:
        st.info("Aucune œuvre ne correspond à vos filtres.")
elif not os.path.exists(IMAGE_DIR):
    st.error(f"Dossier introuvable : {IMAGE_DIR}")
else:
    st.warning("Aucune image trouvée dans le dossier.")
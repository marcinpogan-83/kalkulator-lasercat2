import streamlit as st
import pandas as pd
import uuid  # Do generowania unikalnych ID wariantów

# --- KONFIGURACJA STRONY (Musi być na samym początku) ---
st.set_page_config(
    page_title="Laser.cat Professional Dashboard",
    page_icon="🐱",
    layout="wide"
)

# --- STYLE CSS (PRO DESIGN) ---
st.markdown("""
    <style>
    .main-header { font-size: 2.5rem; color: #FF4B4B; font-weight: 700; margin-bottom: 0px; }
    .sub-header { font-size: 1.2rem; color: #555; margin-bottom: 20px; }
    .metric-card { background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #FF4B4B; }
    .stButton>button { width: 100%; font-weight: bold; }
    div[data-testid="stExpander"] details summary { font-weight: bold; font-size: 1.1rem; }
    </style>
    """, unsafe_allow_html=True)

# --- INICJALIZACJA BAZY DANYCH (SESSION STATE) ---
if 'materials_db' not in st.session_state:
    # Baza materiałów z cenami bazowymi (za formatkę/arkusz roboczy)
    data = [
        {"Kategoria": "Sklejka", "Nazwa": "Sklejka 3mm", "Cena Bazowa (PLN)": 2.90},
        {"Kategoria": "Sklejka", "Nazwa": "Sklejka 4mm", "Cena Bazowa (PLN)": 3.40},
        {"Kategoria": "Sklejka", "Nazwa": "Sklejka 5mm", "Cena Bazowa (PLN)": 4.20},
        {"Kategoria": "Sklejka", "Nazwa": "Sklejka 6mm", "Cena Bazowa (PLN)": 5.20},
        {"Kategoria": "Sklejka", "Nazwa": "Sklejka 8-10mm", "Cena Bazowa (PLN)": 8.50},
        {"Kategoria": "HDF/MDF", "Nazwa": "HDF 3mm", "Cena Bazowa (PLN)": 2.50},
        {"Kategoria": "Pleksi", "Nazwa": "Pleksi 2-3mm", "Cena Bazowa (PLN)": 3.00},
        {"Kategoria": "Pleksi", "Nazwa": "Pleksi 4-5mm", "Cena Bazowa (PLN)": 5.00},
        {"Kategoria": "Inne", "Nazwa": "Filc", "Cena Bazowa (PLN)": 2.50},
        {"Kategoria": "Inne", "Nazwa": "Papier/Karton", "Cena Bazowa (PLN)": 2.00},
    ]
    st.session_state.materials_db = pd.DataFrame(data)

if 'variants' not in st.session_state:
    st.session_state.variants = []

# --- STAWKI OPERACYJNE (MOŻNA WYNIEŚĆ DO SIDEBARA) ---
CUTTING_RATE_PLN_M = 2.50  # Cena za metr bieżący cięcia
ENGRAVING_RATE_PLN_CM2 = 0.20 # Cena za cm2 graweru

# --- LOGIKA HYBRYDOWEGO RABATOWANIA ---
def calculate_auto_discount(qty):
    """Zwraca sugerowany % rabatu na podstawie ilości."""
    if qty >= 100: return 15.0
    if qty >= 50: return 10.0
    if qty >= 10: return 5.0
    return 0.0

# Inicjalizacja zmiennych pomocniczych do śledzenia zmian ilości
if 'last_quantity' not in st.session_state:
    st.session_state.last_quantity = 1
if 'discount_val' not in st.session_state:
    st.session_state.discount_val = 0.0

# --- SIDEBAR: ZARZĄDZANIE BAZĄ ---
with st.sidebar:
    st.image("https://placehold.co/200x80?text=Laser.cat+PRO", use_container_width=True)
    st.header("🗄️ Baza Materiałów")
    
    edited_db = st.data_editor(
        st.session_state.materials_db,
        num_rows="dynamic",
        use_container_width=True,
        key="editor"
    )
    st.session_state.materials_db = edited_db
    
    st.divider()
    st.caption("Ceny w bazie to ceny netto za arkusz/jednostkę bazową.")

# --- GŁÓWNY INTERFEJS ---
st.markdown('<div class="main-header">Kalkulator Ofertowy 3000</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">System wyceny precyzyjnej z kontrolą marży</div>', unsafe_allow_html=True)

# 1. KONFIGURACJA ZLECENIA
col_main_1, col_main_2 = st.columns([2, 1])

with col_main_1:
    st.subheader("1. Parametry Techniczne")
    c1, c2 = st.columns(2)
    
    with c1:
        # Pobieranie listy materiałów
        mat_options = st.session_state.materials_db.apply(
            lambda x: f"{x['Nazwa']} ({x['Cena Bazowa (PLN)']:.2f} zł)", axis=1
        ).tolist()
        selected_mat_str = st.selectbox("Materiał:", mat_options)
        
        # Wyciąganie ceny bazowej z wyboru
        selected_row = st.session_state.materials_db[
            st.session_state.materials_db.apply(lambda x: f"{x['Nazwa']} ({x['Cena Bazowa (PLN)']:.2f} zł)", axis=1) == selected_mat_str
        ].iloc[0]
        base_material_price = selected_row['Cena Bazowa (PLN)']

    with c2:
        # Obsługa zmiany ilości -> aktualizacja rabatu
        quantity = st.number_input("Ilość (szt):", min_value=1, value=st.session_state.last_quantity, step=1)
        
        # LOGIKA REACTIVE DEFAULTS
        # Jeśli ilość się zmieniła, zaktualizuj sugerowany rabat
        if quantity != st.session_state.last_quantity:
            st.session_state.discount_val = calculate_auto_discount(quantity)
            st.session_state.last_quantity = quantity
            st.rerun() # Przeładuj, żeby zaktualizować pole rabatu

    c3, c4 = st.columns(2)
    with c3:
        cutting_length = st.number_input("Długość linii cięcia (mb):", min_value=0.0, value=1.5, step=0.1, help="Suma linii cięcia dla JEDNEJ sztuki")
    with c4:
        engraving_area = st.number_input("Powierzchnia graweru (cm²):", min_value=0.0, value=0.0, step=10.0, help="Dla JEDNEJ sztuki")

with col_main_2:
    st.subheader("2. Rabaty i Dopłaty")
    
    # HYBRYDOWE POLE RABATU
    # Użytkownik widzi sugestię, ale może ją zmienić
    discount_percent = st.number_input(
        f"Rabat (%) [Sugerowany: {calculate_auto_discount(quantity)}%]",
        min_value=0.0, 
        max_value=100.0, 
        value=st.session_state.discount_val,
        step=1.0,
        key="discount_input"
    )
    # Synchronizacja manualnej zmiany rabatu ze stanem
    st.session_state.discount_val = discount_percent

    st.markdown("---")
    st.markdown("**Koszty Stałe (Jednorazowe)**")
    setup_fee = st.number_input("Opłata Startowa (Setup):", value=30.0, step=10.0)
    
    c_design_1, c_design_2 = st.columns(2)
    with c_design_1:
        design_hours = st.number_input("Godziny grafika:", min_value=0.0, value=0.0, step=0.5)
    with c_design_2:
        design_rate = st.number_input("Stawka h:", value=100.0, step=10.0)

# --- OBLICZENIA (SILNIK) ---

# A. Koszty jednostkowe
# 1. Materiał: (Cena * 1.2 odpad) + 15% marży
material_unit_cost = (base_material_price * 1.2) * 1.15
# 2. Obróbka
cutting_unit_cost = cutting_length * CUTTING_RATE_PLN_M
engraving_unit_cost = engraving_area * ENGRAVING_RATE_PLN_CM2

unit_base_netto = material_unit_cost + cutting_unit_cost + engraving_unit_cost

# B. Koszty całkowite produkcji
production_total_netto = unit_base_netto * quantity

# C. Zastosowanie Rabatu (tylko na produkcję, nie na usługi dodatkowe)
discount_amount = production_total_netto * (discount_percent / 100)
production_after_discount = production_total_netto - discount_amount

# D. Usługi dodatkowe
services_cost = setup_fee + (design_hours * design_rate)

# E. SUMA KOŃCOWA
final_netto = production_after_discount + services_cost
final_brutto = final_netto * 1.23

# --- PREZENTACJA WYNIKU ---
st.divider()

col_res_1, col_res_2, col_res_3 = st.columns([1, 1, 2])

with col_res_1:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.caption("Cena jednostkowa (Netto)")
    unit_final = (production_after_discount / quantity) if quantity > 0 else 0
    st.markdown(f"### {unit_final:.2f} PLN")
    st.markdown("</div>", unsafe_allow_html=True)

with col_res_2:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.caption("Wartość Rabatu")
    st.markdown(f"### -{discount_amount:.2f} PLN")
    st.markdown("</div>", unsafe_allow_html=True)

with col_res_3:
    st.success(f"### SUMA OFERTY (NETTO): {final_netto:.2f} PLN")
    st.caption(f"Brutto (23% VAT): {final_brutto:.2f} PLN")

# --- ZAPISYWANIE WARIANTU ---
variant_name = st.text_input("Nazwa wariantu (opcjonalnie):", placeholder="np. Wersja Economy - Sklejka 3mm")

if st.button("💾 DODAJ WARIANT DO PORÓWNANIA", use_container_width=True, type="primary"):
    new_variant = {
        "ID": str(uuid.uuid4())[:8],
        "Nazwa": variant_name if variant_name else f"Wariant {len(st.session_state.variants)+1}",
        "Materiał": selected_row['Nazwa'],
        "Ilość": quantity,
        "Rabat %": f"{discount_percent:.1f}%",
        "Cena Jedn. Netto": f"{unit_final:.2f} PLN",
        "Usługi (Grafik/Setup)": f"{services_cost:.2f} PLN",
        "SUMA NETTO": final_netto, # liczba do sumowania
        "SUMA NETTO (Display)": f"{final_netto:.2f} PLN"
    }
    st.session_state.variants.append(new_variant)
    st.toast("Wariant został dodany!", icon="✅")

# --- TABELA WARIANTÓW ---
if st.session_state.variants:
    st.divider()
    st.subheader("📋 Zapisane Warianty Oferty")
    
    df_variants = pd.DataFrame(st.session_state.variants)
    
    # Wyświetlamy ładną tabelę (bez kolumny surowej liczby SUMA NETTO)
    display_cols = ["Nazwa", "Materiał", "Ilość", "Rabat %", "Cena Jedn. Netto", "Usługi (Grafik/Setup)", "SUMA NETTO (Display)"]
    st.dataframe(df_variants[display_cols], use_container_width=True, hide_index=True)
    
    # Suma łączna (jeśli klient bierze kilka wariantów na raz)
    total_offer_sum = df_variants["SUMA NETTO"].sum()
    st.markdown(f"<h3 style='text-align: right'>Łączna wartość wszystkich wariantów: {total_offer_sum:.2f} PLN netto</h3>", unsafe_allow_html=True)
    
    # Opcja czyszczenia
    if st.button("Wyczyść tabelę wariantów"):
        st.session_state.variants = []
        st.rerun()

# --- STOPKA ---
st.markdown("---")
st.caption("Laser.cat System | Created by Python Architect")

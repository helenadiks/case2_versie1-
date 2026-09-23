import streamlit as st
import pandas as pd
import plotly.express as px
.
# Pagina-instellingen
st.set_page_config(
    page_title="Klimaatbeleid vs. Realiteit", 
    layout="wide"
)

# Data inladen, opschonen en transformeren
@st.cache_data
def load_data():
    df_co2 = pd.read_csv('data/annual-co2-emissions-per-country.csv')
    df_ren = pd.read_csv('data/renewable_energy_share_2000_2025.csv')
    
    # Kolommen hernoemen voor eenduidigheid
    df_co2.rename(columns={
        'Entity': 'country_co2', 
        'Code': 'iso_code', 
        'Year': 'year', 
        'Annual CO₂ emissions': 'co2_emissions'
    }, inplace=True)
    
    raw_co2_count = len(df_co2)
    raw_ren_count = len(df_ren)
    
    # Filteren op geldige ISO3-landcodes (3 letters, sluit continenten/regio's uit)
    df_co2_clean = df_co2[df_co2['iso_code'].notna() & (df_co2['iso_code'].str.len() == 3)].copy()
    df_ren_clean = df_ren[df_ren['iso_code'].notna() & (df_ren['iso_code'].str.len() == 3)].copy()
    
    # Inner Join op ISO3-landcode + jaar
    merged = pd.merge(df_co2_clean, df_ren_clean, on=['iso_code', 'year'], how='inner')
    
    # Feature Engineering (veilig omgaan met deling door nul of afwezige bevolking)
    merged['gdp_per_capita'] = merged.apply(
        lambda r: r['gdp'] / r['population'] if pd.notna(r['population']) and r['population'] > 0 else None, axis=1
    )
    merged['co2_per_capita'] = merged.apply(
        lambda r: r['co2_emissions'] / r['population'] if pd.notna(r['population']) and r['population'] > 0 else None, axis=1
    )
    
    # Inkomenscategorieën toevoegen voor deelvraag 3
    bins = [-float('inf'), 5000, 20000, float('inf')]
    labels = ['Lage inkomens (< $5k)', 'Opkomende inkomens ($5k-$20k)', 'Hoge inkomens (> $20k)']
    merged['income_group'] = pd.cut(merged['gdp_per_capita'], bins=bins, labels=labels)
    # Voeg een categorie toe voor onbekend/geen data om fouten te voorkomen
    merged['income_group'] = merged['income_group'].astype(str).replace({'nan': 'Onbekend / Geen BBP'})
    
    stats = {
        'raw_co2': raw_co2_count,
        'raw_ren': raw_ren_count,
        'clean_co2': len(df_co2_clean),
        'clean_ren': len(df_ren_clean),
        'merged': len(merged)
    }
    
    return merged, stats

# Data laden
try:
    df, stats = load_data()
except Exception as e:
    st.error(f"Fout bij het laden van de bestanden: {e}")
    st.stop()

# Datumbereik bepalen
min_jaar = int(df['year'].min())
max_jaar = int(df['year'].max())

# Hoofdtitel & Onderzoeksvraag
st.title("Klimaatbeleid vs. Realiteit")
st.markdown(
    "**Onderzoeksvraag:** *In hoeverre komt de transitie naar hernieuwbare energie "
    "daadwerkelijk tot uiting in dalende CO₂-uitstoot, en hoe verhoudt dit zich tot het inkomensniveau van landen?*"
)

# Zijbalk (Interactieve Controls)
st.sidebar.header("Filters")
selected_year = st.sidebar.slider("Selecteer een jaar", min_value=min_jaar, max_value=max_jaar, value=max_jaar)

# LANDENFILTER
landen_lijst = sorted(df['country'].unique())
selected_countries = st.sidebar.multiselect(
    "Filter op specifieke landen",
    options=landen_lijst,
    default=[],
    help="Laat leeg om alle landen te analyseren"
)

income_options = ["Alle inkomensgroepen", "Hoge inkomens (> $20k)", "Opkomende inkomens ($5k-$20k)", "Lage inkomens (< $5k)"]
selected_income = st.sidebar.selectbox("Filter op inkomensniveau", income_options)

use_log_scale = st.sidebar.checkbox("Logaritmische schaal voor GDP", value=True)

# Dataselectie filteren op basis van zijbalk
df_year = df[df['year'] == selected_year].copy()

# TOEPASSEN LANDENFILTER OP DF_YEAR
if selected_countries:
    df_year = df_year[df_year['country'].isin(selected_countries)]

if selected_income == "Hoge inkomens (> $20k)":
    df_year = df_year[df_year['income_group'] == 'Hoge inkomens (> $20k)']
elif selected_income == "Opkomende inkomens ($5k-$20k)":
    df_year = df_year[df_year['income_group'] == 'Opkomende inkomens ($5k-$20k)']
elif selected_income == "Lage inkomens (< $5k)":
    df_year = df_year[df_year['income_group'] == 'Lage inkomens (< $5k)']

# Kerncijfers van de gekozen selectie
col1, col2, col3, col4 = st.columns(4)
col1.metric("Aantal analyseerde landen", len(df_year))
col2.metric("Gem. hernieuwbare stroom", f"{df_year['renewables_share_elec'].mean():.1f}%" if len(df_year) > 0 and not df_year['renewables_share_elec'].isna().all() else "N/B")
col3.metric("Gem. CO₂ per inwoner", f"{df_year['co2_per_capita'].mean():.2f} ton" if len(df_year) > 0 and not df_year['co2_per_capita'].isna().all() else "N/B")
col4.metric("Gem. GDP per inwoner", f"${df_year['gdp_per_capita'].mean():,.0f}" if len(df_year) > 0 and not df_year['gdp_per_capita'].isna().all() else "N/B")

st.divider()

# Tabbladen gekoppeld aan de deelvragen
tab1, tab2, tab3, tab4 = st.tabs([
    "1. Environmental Kuznets Curve", 
    "2. Walk vs. Talk (Ontkoppeling)", 
    "3. Geografisch & Tijdverloop", 
    "Data & Methodologie"
])

# -----------------------------------------------------------------------------
# TAB 1: Environmental Kuznets Curve & Inkomensverschillen (Deelvraag 2 & 3)
# -----------------------------------------------------------------------------
with tab1:
    st.subheader(f"Deelvraag 2 & 3: Welvaart vs. CO₂-uitstoot ({selected_year})")
    st.write(
        "Hier onderzoeken we of er bewijs is voor een **Environmental Kuznets Curve**: "
        "stijgt CO₂-uitstoot mee met GDP per capita tot een bepaald welvaartsniveau, om daarna af te vlakken of te dalen?"
    )
    
    # Filter uitvallers zonder BBP/Bevolking voor de EKC-plot
    df_ekc_clean = df_year.dropna(subset=['gdp_per_capita', 'co2_per_capita', 'population'])
    
    if len(df_ekc_clean) == 0:
        st.warning("Er zijn geen volledige gegevens (BBP en CO₂ per inwoner) beschikbaar voor de huidige selectie.")
    else:
        fig_ekc = px.scatter(
            df_ekc_clean,
            x="gdp_per_capita",
            y="co2_per_capita",
            size="population",
            color="income_group",
            hover_name="country",
            log_x=use_log_scale,
            labels={
                "gdp_per_capita": "GDP per inwoner (USD)",
                "co2_per_capita": "CO₂ per inwoner (ton)",
                "income_group": "Inkomensgroep",
                "population": "Bevolking"
            },
            title=f"Koppelverband GDP vs CO₂ per inwoner per inkomensgroep ({selected_year})"
        )
        st.plotly_chart(fig_ekc, use_container_width=True)
    
    st.markdown("""
    **Analyse & Inzichten:**
    - **Lage inkomens:** Laten over het algemeen zowel een lage CO₂-uitstoot per inwoner als een laag GDP zien.
    - **Opkomende inkomens:** Laten vaak de sterkste stijging in CO₂-uitstoot zien naarmate de industrie en economie groeien.
    - **Hoge inkomens:** Welvarende landen vertonen meer spreiding; meerdere hoge-inkomenslanden slagen erin hun uitstoot per inwoner af te laten vlakken of te verlagen (de zogeheten 'groene ontkoppeling').
    """)

# -----------------------------------------------------------------------------
# TAB 2: Walk vs. Talk (Deelvraag 1)
# -----------------------------------------------------------------------------
with tab2:
    st.subheader(f"Deelvraag 1: Reële ontkoppeling ('Walk') vs. Beleidsintenties ('Talk') ({min_jaar} vs. {max_jaar})")
    st.write(
        "We vergelijken de verandering in hernieuwbare energie met de daadwerkelijke procentuele verandering "
        "in CO₂-uitstoot per inwoner tussen het begin- en eindjaar."
    )
    
    df_start = df[df['year'] == min_jaar][['iso_code', 'co2_per_capita', 'renewables_share_elec']]
    df_recent = df[df['year'] == max_jaar][['iso_code', 'country', 'co2_per_capita', 'renewables_share_elec', 'income_group']]
    df_change = pd.merge(df_start, df_recent, on='iso_code', suffixes=(f'_{min_jaar}', f'_{max_jaar}'))
    
    # TOEPASSEN LANDENFILTER OP DF_CHANGE
    if selected_countries:
        df_change = df_change[df_change['country'].isin(selected_countries)]
        
    # Verwijder rijen met ontbrekende start- of eindwaarden
    df_change = df_change.dropna(subset=[f'co2_per_capita_{min_jaar}', f'co2_per_capita_{max_jaar}', f'renewables_share_elec_{min_jaar}', f'renewables_share_elec_{max_jaar}'])
    
    if len(df_change) == 0:
        st.warning("Er zijn onvoldoende historische gegevens beschikbaar voor de gekozen selectie om de ontkoppeling te berekenen.")
    else:
        df_change['co2_pct_change'] = ((df_change[f'co2_per_capita_{max_jaar}'] - df_change[f'co2_per_capita_{min_jaar}']) / df_change[f'co2_per_capita_{min_jaar}']) * 100
        df_change['ren_diff'] = df_change[f'renewables_share_elec_{max_jaar}'] - df_change[f'renewables_share_elec_{min_jaar}']
        
        def categoriseer(row):
            if row['ren_diff'] > 5 and row['co2_pct_change'] < 0:
                return 'Walk: Groene daling (Meer hernieuwbaar & minder CO₂)'
            elif row['ren_diff'] > 5 and row['co2_pct_change'] >= 0:
                return 'Talk/Lag: Meer hernieuwbaar, maar CO₂ stijgt toch'
            elif row['ren_diff'] <= 5 and row['co2_pct_change'] < 0:
                return 'Passieve daling (Minder CO₂ zonder grote groene groei)'
            else:
                return 'Achterblijvers (Weinig groene groei & stijgende CO₂)'

        df_change['Categorie'] = df_change.apply(categoriseer, axis=1)
        
        fig_walk = px.scatter(
            df_change,
            x="ren_diff",
            y="co2_pct_change",
            color="Categorie",
            hover_name="country",
            labels={
                "ren_diff": "Toename hernieuwbare stroom (%-punt)",
                "co2_pct_change": "Verandering CO₂ per inwoner (%)"
            },
            title=f"Toename hernieuwbaar vs. Verandering CO₂-uitstoot ({min_jaar}-{max_jaar})"
        )
        fig_walk.add_hline(y=0, line_dash="dash", line_color="gray")
        fig_walk.add_vline(x=5, line_dash="dash", line_color="gray")
        st.plotly_chart(fig_walk, use_container_width=True)
    
    st.markdown("""
    **Categorie-indeling:**
    - **Walk (Linksonder/Rechtsonder onder y=0 & x>5):** Landen die hun aandeel hernieuwbare energie met meer dan 5 percentagepunten zagen stijgen én een effectieve daling in CO₂ per inwoner wisten te realiseren.
    - **Talk / Lag (Rechtsboven):** Landen waar het aandeel hernieuwbare energie wel steeg, maar waar de totale vraag naar energie of de fossiele mix zo sterk groeide dat de CO₂-uitstoot per inwoner per saldo toch toenam.
    """)

# -----------------------------------------------------------------------------
# TAB 3: Geografische Spreiding & Tijdverloop (Hoofdvraag)
# -----------------------------------------------------------------------------
with tab3:
    st.subheader(f"Geografische verdeling van hernieuwbare energie ({selected_year})")
    
    fig_map = px.choropleth(
        df_year,
        locations="iso_code",
        color="renewables_share_elec",
        hover_name="country",
        color_continuous_scale="Greens",
        labels={"renewables_share_elec": "% Hernieuwbare stroom"}
    )
    st.plotly_chart(fig_map, use_container_width=True)
    
    st.divider()
    
    st.subheader("Verloop per land over de tijd")
    gekozen_land = st.selectbox("Selecteer een land voor de tijdreeks", landen_lijst, index=landen_lijst.index("Netherlands") if "Netherlands" in landen_lijst else 0)
    
    df_land = df[df['country'] == gekozen_land].sort_values("year")
    
    # Checken of land data heeft
    if df_land[['renewables_share_elec', 'co2_per_capita']].dropna(how='all').empty:
        st.warning(f"Er is geen tijdsreeksdata voor {gekozen_land} beschikbaar.")
    else:
        fig_line = px.line(
            df_land,
            x="year",
            y=["renewables_share_elec", "co2_per_capita"],
            labels={"value": "Waarde", "year": "Jaar", "variable": "Variabele"},
            title=f"Historische ontwikkeling in {gekozen_land}"
        )
        fig_line.add_vline(x=2015, line_dash="dot", line_color="blue", annotation_text="Parijs-akkoord (2015)")
        st.plotly_chart(fig_line, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 4: Data & Methodologie
# -----------------------------------------------------------------------------
with tab4:
    st.subheader("Data-integratie & Opschoning")
    st.write(
        "De analyse combineert twee datasets op basis van een **inner join** op de samengestelde sleutel `(iso_code, year)`. "
        "Alleen geldige 3-letterige ISO3-landcodes worden meegenomen om aggregaatrijen (zoals continenten en de wereld) uit te sluiten."
    )
    
    st.write("**Relationale verantwoording aantallen rijen:**")
    st.write(f"- CO₂-dataset (ruw): {stats['raw_co2']:,} rijen")
    st.write(f"- CO₂-dataset (na filtering op ISO3-landcodes): {stats['clean_co2']:,} rijen")
    st.write(f"- Hernieuwbare energie dataset (ruw): {stats['raw_ren']:,} rijen")
    st.write(f"- Hernieuwbare energie dataset (na filtering op ISO3-landcodes): {stats['clean_ren']:,} rijen")
    st.write(f"- **Samengevoegde analyse-dataset (Inner Join):** {stats['merged']:,} rijen")
    
    st.divider()
    
    st.subheader("Bronvermelding & Datasets")
    st.write("- **CO₂ Emissions Across Countries, Regions & Sectors:** Kaggle / Our World in Data")
    st.write("- **Renewable Energy Share by Country 2000-2025:** Kaggle / Our World in Data / Ember / Energy Institute")
    st.write("- **Software & Libraries:** Python, Streamlit, Pandas, Plotly Express")
    
    st.write("**Voorbeeldweergave van het gecombineerde dataframe:**")
    st.dataframe(df_year[['iso_code', 'country', 'year', 'co2_emissions', 'co2_per_capita', 'renewables_share_elec', 'gdp_per_capita', 'income_group']].head(15))

import glob
import os

import streamlit as st
import pandas as pd
import plotly.express as px
import kagglehub

st.set_page_config(
    page_title="Klimaatbeleid vs. realiteit",
    layout="wide"
)


LABELS = {
    "country": "Land",
    "iso_code": "Landcode",
    "year": "Jaar",
    "co2_emissions": "CO2-uitstoot (ton)",
    "co2_per_capita": "CO2 per inwoner (ton)",
    "gdp": "GDP (USD)",
    "gdp_per_capita": "GDP per inwoner (USD)",
    "population": "Bevolking",
    "renewables_share_elec": "Aandeel hernieuwbare stroom (%)",
    "income_group": "Inkomensgroep",
    "ren_diff": "Toename hernieuwbare stroom (procentpunt)",
    "co2_pct_change": "Verandering CO2 per inwoner (%)",
    "Categorie": "Categorie",
}


@st.cache_data
def load_data():
    #  Datasets ophalen via de Kaggle API (kagglehub) 
    
    co2_path = kagglehub.dataset_download("vishnupriyan123/annual-co2-emissions-per-country")
    ren_path = kagglehub.dataset_download("elvisbui/renewable-energy-share-by-country-2000-2025")

    co2_csv = glob.glob(os.path.join(co2_path, "*.csv"))[0]
    ren_csv = glob.glob(os.path.join(ren_path, "*.csv"))[0]

    df_co2 = pd.read_csv(co2_csv)
    df_ren = pd.read_csv(ren_csv)

    #  Kolomnamen meteen na het inladen aanpassen 

    df_co2.rename(columns={
        "Entity": "country",
        "Code": "iso_code",
        "Year": "year",
        "Annual CO₂ emissions": "co2_emissions",
    }, inplace=True)

    raw_co2_count = len(df_co2)
    raw_ren_count = len(df_ren)

    # Filteren op geldige ISO3-landcodes 
    # Sluit continenten, regio's en inkomensgroepen uit (die hebben
    # geen 3-letterige landcode).
    df_co2_clean = df_co2[df_co2["iso_code"].notna() & (df_co2["iso_code"].str.len() == 3)].copy()
    df_ren_clean = df_ren[df_ren["iso_code"].notna() & (df_ren["iso_code"].str.len() == 3)].copy()

    #  Antarctica expliciet verwijderen 
    
    df_co2_clean = df_co2_clean[df_co2_clean["iso_code"] != "ATA"]
    df_ren_clean = df_ren_clean[df_ren_clean["iso_code"] != "ATA"]

    # Beide bestanden hebben een kolom "country" (niet de join-sleutel).
    # Zonder ingrijpen krijg je na de merge "country_x"/"country_y".
    # De co2-dataset blijft leidend voor de landnaam.
    df_ren_clean = df_ren_clean.drop(columns=["country"])

    # Inner join op landcode + jaar
    merged = pd.merge(df_co2_clean, df_ren_clean, on=["iso_code", "year"], how="inner")

    #  Afgeleide kolommen
    merged["gdp_per_capita"] = merged.apply(
        lambda r: r["gdp"] / r["population"] if pd.notna(r["population"]) and r["population"] > 0 else None, axis=1
    )
    merged["co2_per_capita"] = merged.apply(
        lambda r: r["co2_emissions"] / r["population"] if pd.notna(r["population"]) and r["population"] > 0 else None, axis=1
    )

    # Inkomenscategorieën
    bins = [-float("inf"), 5000, 20000, float("inf")]
    labels_inkomen = ["Lage inkomens (< $5k)", "Opkomende inkomens ($5k-$20k)", "Hoge inkomens (> $20k)"]
    merged["income_group"] = pd.cut(merged["gdp_per_capita"], bins=bins, labels=labels_inkomen)
    merged["income_group"] = merged["income_group"].astype(str).replace({"nan": "Onbekend / geen GDP-data"})

    stats = {
        "raw_co2": raw_co2_count,
        "raw_ren": raw_ren_count,
        "clean_co2": len(df_co2_clean),
        "clean_ren": len(df_ren_clean),
        "merged": len(merged),
        "totaal_landen": merged["iso_code"].nunique(),
        "landen_zonder_gdp": merged[merged["gdp"].isna()]["iso_code"].nunique(),
    }

    return merged, stats


# Data laden
try:
    df, stats = load_data()
except Exception as e:
    st.error(
        "Fout bij het laden van de datasets via Kaggle. Controleer of er een geldige "
        f"Kaggle API-sleutel is ingesteld. Foutmelding: {e}"
    )
    st.stop()

# Datumbereik bepalen
min_jaar = int(df["year"].min())
max_jaar = int(df["year"].max())


st.title("Klimaatbeleid vs. realiteit")
st.markdown(
    "**Onderzoeksvraag:** *in hoeverre komt de transitie naar hernieuwbare energie "
    "daadwerkelijk tot uiting in dalende CO2-uitstoot, en hoe verhoudt dit zich tot "
    "het inkomensniveau van landen?*"
)
st.caption(
    "Het dashboard doorloopt dit in vier stappen: eerst of landen hun beloftes waarmaken, "
    "dan de relatie met welvaart, gevolgd door een geografisch overzicht en tot slot de "
    "verantwoording van de gebruikte data."
)

st.sidebar.header("Filters")
selected_year = st.sidebar.slider("Selecteer een jaar", min_value=min_jaar, max_value=max_jaar, value=max_jaar)

landen_lijst = sorted(df["country"].unique())
selected_countries = st.sidebar.multiselect(
    "Filter op specifieke landen",
    options=landen_lijst,
    default=[],
    help="Laat leeg om alle landen te analyseren",
)

income_options = ["Alle inkomensgroepen", "Hoge inkomens (> $20k)", "Opkomende inkomens ($5k-$20k)", "Lage inkomens (< $5k)"]
selected_income = st.sidebar.selectbox("Filter op inkomensniveau", income_options)

use_log_scale = st.sidebar.checkbox("Logaritmische schaal voor GDP", value=True)

# Dataselectie filteren op basis van zijbalk
df_year = df[df["year"] == selected_year].copy()

if selected_countries:
    df_year = df_year[df_year["country"].isin(selected_countries)]

if selected_income != "Alle inkomensgroepen":
    df_year = df_year[df_year["income_group"] == selected_income]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Aantal geanalyseerde landen", len(df_year))
col2.metric(
    "Gemiddeld aandeel hernieuwbare stroom",
    f"{df_year['renewables_share_elec'].mean():.1f}%" if len(df_year) > 0 and not df_year["renewables_share_elec"].isna().all() else "Onbekend",
)
col3.metric(
    "Gemiddelde CO2-uitstoot per inwoner",
    f"{df_year['co2_per_capita'].mean():.2f} ton" if len(df_year) > 0 and not df_year["co2_per_capita"].isna().all() else "Onbekend",
)
col4.metric(
    "Gemiddeld GDP per inwoner",
    f"${df_year['gdp_per_capita'].mean():,.0f}" if len(df_year) > 0 and not df_year["gdp_per_capita"].isna().all() else "Onbekend",
)

st.divider()


tab1, tab2, tab3, tab4 = st.tabs([
    "Walk vs. talk",
    "CO2 vs. welvaart",
    "Kaart en tijdlijn",
    "Data en methode",
])


with tab1:
    st.subheader(f"Praat een land de talk, of loopt het ook de walk? ({min_jaar} versus {max_jaar})")
    st.caption(
        "Vergelijkt de toename in hernieuwbare energie met de werkelijke verandering in "
        "CO2-uitstoot per inwoner, tussen het eerste en het laatste jaar in de data."
    )

    df_start = df[df["year"] == min_jaar][["iso_code", "co2_per_capita", "renewables_share_elec"]]
    df_recent = df[df["year"] == max_jaar][["iso_code", "country", "co2_per_capita", "renewables_share_elec", "income_group"]]
    df_change = pd.merge(df_start, df_recent, on="iso_code", suffixes=(f"_{min_jaar}", f"_{max_jaar}"))

    if selected_countries:
        df_change = df_change[df_change["country"].isin(selected_countries)]

    df_change = df_change.dropna(subset=[
        f"co2_per_capita_{min_jaar}", f"co2_per_capita_{max_jaar}",
        f"renewables_share_elec_{min_jaar}", f"renewables_share_elec_{max_jaar}",
    ])

    if len(df_change) == 0:
        st.warning("Er is onvoldoende data beschikbaar voor de gekozen selectie om dit te berekenen.")
    else:
        df_change["co2_pct_change"] = (
            (df_change[f"co2_per_capita_{max_jaar}"] - df_change[f"co2_per_capita_{min_jaar}"])
            / df_change[f"co2_per_capita_{min_jaar}"]
        ) * 100
        df_change["ren_diff"] = df_change[f"renewables_share_elec_{max_jaar}"] - df_change[f"renewables_share_elec_{min_jaar}"]

        def categoriseer(row):
            if row["ren_diff"] > 5 and row["co2_pct_change"] < 0:
                return "Walk: groene daling (meer hernieuwbaar en minder CO2)"
            elif row["ren_diff"] > 5 and row["co2_pct_change"] >= 0:
                return "Talk: meer hernieuwbaar, maar CO2 stijgt toch"
            elif row["ren_diff"] <= 5 and row["co2_pct_change"] < 0:
                return "Passieve daling (minder CO2 zonder grote groene groei)"
            else:
                return "Achterblijver (weinig groene groei en stijgende CO2)"

        df_change["Categorie"] = df_change.apply(categoriseer, axis=1)

        fig_walk = px.scatter(
            df_change,
            x="ren_diff",
            y="co2_pct_change",
            color="Categorie",
            hover_name="country",
            labels=LABELS,
            title=f"Toename hernieuwbare stroom versus CO2-verandering ({min_jaar} tot {max_jaar})",
        )
        fig_walk.add_hline(y=0, line_dash="dash", line_color="gray")
        fig_walk.add_vline(x=5, line_dash="dash", line_color="gray")
        st.plotly_chart(fig_walk, use_container_width=True)

    st.markdown(
        "**Hoe lees je dit:** landen rechtsonder (meer hernieuwbare stroom, minder CO2) "
        "maken hun belofte waar. Landen rechtsboven zagen hun aandeel hernieuwbaar wel "
        "stijgen, maar hun CO2-uitstoot per inwoner steeg per saldo toch, bijvoorbeeld "
        "doordat de totale energievraag harder groeide dan de omschakeling."
    )


with tab2:
    st.subheader(f"Stijgt CO2-uitstoot mee met welvaart? ({selected_year})")
    st.caption(
        "Onderzoekt of er bewijs is voor een zogeheten Environmental Kuznets Curve: "
        "stijgt CO2-uitstoot mee met GDP per inwoner tot een bepaald niveau, om daarna "
        "af te vlakken of te dalen?"
    )

    df_ekc_clean = df_year.dropna(subset=["gdp_per_capita", "co2_per_capita", "population"])

    if len(df_ekc_clean) == 0:
        st.warning("Er zijn geen volledige gegevens (GDP en CO2 per inwoner) beschikbaar voor de huidige selectie.")
    else:
        fig_ekc = px.scatter(
            df_ekc_clean,
            x="gdp_per_capita",
            y="co2_per_capita",
            size="population",
            color="income_group",
            hover_name="country",
            log_x=use_log_scale,
            labels=LABELS,
            title=f"GDP versus CO2-uitstoot per inkomensgroep ({selected_year})",
        )
        st.plotly_chart(fig_ekc, use_container_width=True)

    st.markdown(
        "**Wat valt op:** lage-inkomenslanden laten meestal zowel een lage CO2-uitstoot "
        "als een laag GDP zien. Opkomende economieën laten vaak de sterkste stijging in "
        "CO2-uitstoot zien naarmate industrie en economie groeien. Bij hoge-inkomenslanden "
        "zie je meer spreiding: sommige slagen erin hun uitstoot per inwoner af te vlakken "
        "of te verlagen, ook wel groene ontkoppeling genoemd."
    )

with tab3:
    st.subheader(f"Aandeel hernieuwbare energie per land ({selected_year})")
    st.caption("Aanvullend bij de vorige twee grafieken: geografische spreiding en verloop per land.")

    fig_map = px.choropleth(
        df_year,
        locations="iso_code",
        color="renewables_share_elec",
        hover_name="country",
        color_continuous_scale="Greens",
        labels=LABELS,
        title=f"Aandeel hernieuwbare stroom per land ({selected_year})",
    )
    st.plotly_chart(fig_map, use_container_width=True)

    st.divider()

    st.subheader("Verloop per land over de tijd")
    gekozen_land = st.selectbox(
        "Selecteer een land voor de tijdlijn",
        landen_lijst,
        index=landen_lijst.index("Netherlands") if "Netherlands" in landen_lijst else 0,
    )

    df_land = df[df["country"] == gekozen_land].sort_values("year")

    if df_land[["renewables_share_elec", "co2_per_capita"]].dropna(how="all").empty:
        st.warning(f"Er is geen tijdreeksdata beschikbaar voor {gekozen_land}.")
    else:
        fig_line = px.line(
            df_land,
            x="year",
            y=["renewables_share_elec", "co2_per_capita"],
            labels={**LABELS, "value": "Waarde", "variable": "Indicator"},
            title=f"Ontwikkeling in {gekozen_land}",
        )
        fig_line.add_vline(x=2015, line_dash="dot", line_color="blue", annotation_text="Klimaatakkoord van Parijs (2015)")
        st.plotly_chart(fig_line, use_container_width=True)


with tab4:
    st.subheader("Hoe de data is opgebouwd")
    st.write(
        "De analyse combineert twee datasets met een inner join op landcode en jaar. "
        "Alleen geldige 3-letterige ISO3-landcodes worden meegenomen, zodat aggregaten "
        "zoals werelddelen en de wereld als geheel buiten de analyse blijven. Antarctica "
        "is apart verwijderd omdat er geen bevolkings- of GDP-cijfers voor bestaan."
    )

    st.write("**Aantal rijen per stap:**")
    st.write(f"- CO2-dataset, ruw: {stats['raw_co2']:,} rijen")
    st.write(f"- CO2-dataset, na opschonen: {stats['clean_co2']:,} rijen")
    st.write(f"- Hernieuwbare-energiedataset, ruw: {stats['raw_ren']:,} rijen")
    st.write(f"- Hernieuwbare-energiedataset, na opschonen: {stats['clean_ren']:,} rijen")
    st.write(f"- Samengevoegde dataset: {stats['merged']:,} rijen, {stats['totaal_landen']} landen")

    st.info(
        f"{stats['landen_zonder_gdp']} van de {stats['totaal_landen']} landen missen GDP-data in "
        "minstens één jaar. Die landen blijven zichtbaar op de kaart en in de tijdlijn (tab 'Kaart "
        "en tijdlijn'), maar vallen weg in de welvaart-analyse (tab 'CO2 vs. welvaart'), omdat daar "
        "een GDP-waarde nodig is om te kunnen plotten."
    )

    st.divider()

    st.subheader("Bronnen")
    st.write("- CO2-uitstoot per land, regio en sector: Kaggle, gebaseerd op Our World in Data")
    st.write("- Aandeel hernieuwbare energie per land, 2000-2025: Kaggle, gebaseerd op Our World in Data, Ember en Energy Institute")
    st.write("- Software: Python, Streamlit, Pandas, Plotly Express, Kagglehub")

    st.write("**Voorbeeld van de samengevoegde data:**")
    preview_cols = ["iso_code", "country", "year", "co2_emissions", "co2_per_capita", "renewables_share_elec", "gdp_per_capita", "income_group"]
    st.dataframe(df_year[preview_cols].rename(columns=LABELS).head(15))

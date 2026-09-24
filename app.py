
import glob
import os

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import kagglehub

st.set_page_config(
    page_title="Transitie en uitstoot: houdt het gelijke tred?",
    layout="wide"
)

# Nette namen voor kolommen, zodat we nergens een technische naam met
# underscore in een titel, as of tabel laten staan.
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
    "co2_verandering": "Verandering CO2 per inwoner t.o.v. vorig jaar (ton)",
    "Categorie": "Categorie",
    "rol": "Rol",
}

# Kleuren uit het gevalideerde, kleurenblind-veilige palet.
COLOR_SEQUENCE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#4a3aa7"]
KLEUR_CONTEXT = "#9AA3AA"   # grijs, voor vergelijkingslanden op de achtergrond
KLEUR_HOOFDROL = "#2a78d6"  # blauw, voor het hoofdland


def zet_kaggle_credentials_klaar():
    # Lokaal gebruiken we gewoon ons eigen kaggle.json. Op Streamlit Cloud
    # bestaat dat bestand niet, dus zetten we onze Kaggle-secrets (als we
    # die hebben ingesteld bij Settings > Secrets) om naar de env vars
    # die kagglehub nodig heeft. Staan er geen secrets, dan gebeurt hier
    # niets en pakt kagglehub gewoon het lokale bestand.
    try:
        if "KAGGLE_USERNAME" in st.secrets and "KAGGLE_KEY" in st.secrets:
            os.environ["KAGGLE_USERNAME"] = st.secrets["KAGGLE_USERNAME"]
            os.environ["KAGGLE_KEY"] = st.secrets["KAGGLE_KEY"]
    except Exception:
        pass


zet_kaggle_credentials_klaar()


@st.cache_data
def load_data():
    # Datasets ophalen via de Kaggle API
    co2_path = kagglehub.dataset_download("vishnupriyan123/annual-co2-emissions-per-country")
    ren_path = kagglehub.dataset_download("elvisbui/renewable-energy-share-by-country-2000-2025")

    co2_csv = glob.glob(os.path.join(co2_path, "*.csv"))[0]
    ren_csv = glob.glob(os.path.join(ren_path, "*.csv"))[0]

    df_co2 = pd.read_csv(co2_csv)
    df_ren = pd.read_csv(ren_csv)

    # Kolomnamen meteen aanpassen
    df_co2.rename(columns={
        "Entity": "country",
        "Code": "iso_code",
        "Year": "year",
        "Annual CO₂ emissions": "co2_emissions",
    }, inplace=True)

    raw_co2_count = len(df_co2)
    raw_ren_count = len(df_ren)

    # Alleen geldige 3-letterige landcodes houden
    df_co2_clean = df_co2[df_co2["iso_code"].notna() & (df_co2["iso_code"].str.len() == 3)].copy()
    df_ren_clean = df_ren[df_ren["iso_code"].notna() & (df_ren["iso_code"].str.len() == 3)].copy()

    # Antarctica eruit
    df_co2_clean = df_co2_clean[df_co2_clean["iso_code"] != "ATA"]
    df_ren_clean = df_ren_clean[df_ren_clean["iso_code"] != "ATA"]

    # Beide bestanden hebben een kolom "country", die halen we uit renew weg
    # zodat we straks niet met country_x/country_y zitten na de merge.
    df_ren_clean = df_ren_clean.drop(columns=["country"])

    # Inner join op landcode + jaar
    merged = pd.merge(df_co2_clean, df_ren_clean, on=["iso_code", "year"], how="inner")
    merged = merged.sort_values(["iso_code", "year"]).reset_index(drop=True)

    merged["gdp_per_capita"] = merged.apply(
        lambda r: r["gdp"] / r["population"] if pd.notna(r["population"]) and r["population"] > 0 else None, axis=1
    )
    merged["co2_per_capita"] = merged.apply(
        lambda r: r["co2_emissions"] / r["population"] if pd.notna(r["population"]) and r["population"] > 0 else None, axis=1
    )

    # Jaar-op-jaar verandering per land. We groeperen op land, anders trekken
    # we de eerste rij van het ene land af van de laatste rij van het vorige.
    merged["co2_verandering"] = merged.groupby("iso_code")["co2_per_capita"].diff()

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


try:
    df, stats = load_data()
except Exception as e:
    st.error(
        "Fout bij het laden van de datasets via Kaggle. Controleer of er een geldige "
        "Kaggle API-sleutel is ingesteld (lokaal: ~/.kaggle/kaggle.json, op Streamlit "
        f"Cloud: de secrets KAGGLE_USERNAME en KAGGLE_KEY). Foutmelding: {e}"
    )
    st.stop()

min_jaar = int(df["year"].min())
max_jaar = int(df["year"].max())

st.title("Transitie en uitstoot: houdt het gelijke tred?")
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
        st.subheader(f"Praat een land de 'talk', of loopt het ook de 'walk'? ({min_jaar} versus {max_jaar})")
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

        n_walk = (df_change["Categorie"].str.startswith("Walk")).sum()
        n_totaal = len(df_change)
        pct_walk = round(100 * n_walk / n_totaal) if n_totaal else 0

        st.subheader(f"Slechts {pct_walk}% van de landen maakt de belofte van hernieuwbare energie ook echt waar")
        st.caption(
            f"Vergelijking van {min_jaar} met {max_jaar}: {n_walk} van de {n_totaal} landen combineren meer "
            "hernieuwbare stroom mét een daling van hun CO2-uitstoot per inwoner. De rest praat, loopt niet, "
            "of boekt vooruitgang zonder dat renewables daarin de hoofdrol speelt."
        )

        # We bepalen de twee voorbeelden voor de annotaties eerst, zodat we
        # de as-schaal daarop kunnen afstemmen in plaats van andersom.
        walk_df = df_change[df_change["Categorie"].str.startswith("Walk")]
        talk_df = df_change[df_change["Categorie"].str.startswith("Talk")]
        beste_walk = walk_df.nsmallest(1, "co2_pct_change").iloc[0] if len(walk_df) > 0 else None
        ergste_talk = talk_df.nlargest(1, "co2_pct_change").iloc[0] if len(talk_df) > 0 else None

        # We begrenzen de as op basis van deze twee voorbeelden (plus 15%
        # marge) in plaats van op het maximum van de data. Eén land met een
        # bijna-nul CO2-uitstoot in het startjaar geeft anders zo'n grote
        # procentuele uitschieter dat de rest van de landen niet meer van
        # elkaar te onderscheiden is.
        y_boven_kandidaten = [v for v in [ergste_talk["co2_pct_change"] if ergste_talk is not None else None, 100] if v is not None]
        y_onder_kandidaten = [v for v in [beste_walk["co2_pct_change"] if beste_walk is not None else None, -20] if v is not None]
        y_boven = max(y_boven_kandidaten) * 1.15
        y_onder = min(y_onder_kandidaten) * 1.15 if min(y_onder_kandidaten) < 0 else min(y_onder_kandidaten) * 0.85
        n_buiten_beeld = int(((df_change["co2_pct_change"] > y_boven) | (df_change["co2_pct_change"] < y_onder)).sum())

        fig_walk = px.scatter(
            df_change,
            x="ren_diff",
            y="co2_pct_change",
            color="Categorie",
            symbol="Categorie",
            hover_name="country",
            labels=LABELS,
            title=f"Toename hernieuwbare stroom versus CO2-verandering ({min_jaar} tot {max_jaar})",
        )
        fig_walk.add_hline(y=0, line_dash="dash", line_color="gray")
        fig_walk.add_vline(x=5, line_dash="dash", line_color="gray")
        fig_walk.update_yaxes(range=[y_onder, y_boven])

        if beste_walk is not None:
            fig_walk.add_annotation(
                x=beste_walk["ren_diff"], y=beste_walk["co2_pct_change"],
                text=f"{beste_walk['country']}: sterkste ontkoppeling",
                showarrow=True, arrowhead=2, ax=40, ay=-30,
            )
        if ergste_talk is not None:
            fig_walk.add_annotation(
                x=ergste_talk["ren_diff"], y=ergste_talk["co2_pct_change"],
                text=f"{ergste_talk['country']}: meer hernieuwbaar, CO2 stijgt toch fors",
                showarrow=True, arrowhead=2, ax=-40, ay=30,
            )

        st.plotly_chart(fig_walk, use_container_width=True)

        if n_buiten_beeld > 0:
            st.caption(
                f"De y-as is ingezoomd tot net voorbij de aangewezen voorbeelden, zodat de meeste landen "
                f"onderscheidbaar blijven. {n_buiten_beeld} land(en) met een extreme procentuele verandering "
                "vallen daardoor buiten beeld; dat komt doordat hun CO2-uitstoot per inwoner in "
                f"{min_jaar} bijna nul was, waardoor elke stijging procentueel enorm uitpakt. Filter op dat "
                "land via de zijbalk om het exacte cijfer te zien."
            )

    st.markdown(
        "**Hoe lees je dit:** landen rechtsonder (meer hernieuwbare stroom, minder CO2) "
        "maken hun belofte waar. Landen rechtsboven zagen hun aandeel hernieuwbaar wel "
        "stijgen, maar hun CO2-uitstoot per inwoner steeg per saldo toch, bijvoorbeeld "
        "doordat de totale energievraag harder groeide dan de omschakeling."
    )

with tab2:
    df_ekc_clean = df_year.dropna(subset=["gdp_per_capita", "co2_per_capita", "population"])

    if len(df_ekc_clean) == 0:
        st.subheader(f"Stijgt CO2-uitstoot mee met welvaart? ({selected_year})")
        st.warning("Er zijn geen volledige gegevens (GDP en CO2 per inwoner) beschikbaar voor de huidige selectie.")
    else:
        # We berekenen de correlatie zodat de titel een bewering wordt, geen label.
        correlatie = df_ekc_clean["gdp_per_capita"].corr(df_ekc_clean["co2_per_capita"])
        if correlatie >= 0.5:
            bewering = f"Rijkere landen stoten in {selected_year} nog altijd flink meer CO2 uit per inwoner"
        elif correlatie <= -0.2:
            bewering = f"In {selected_year} stoten rijkere landen juist minder CO2 uit per inwoner"
        else:
            bewering = f"Welvaart en CO2-uitstoot per inwoner hangen in {selected_year} nauwelijks samen"

        st.subheader(bewering)
        st.caption(
            f"Correlatie tussen GDP per inwoner en CO2 per inwoner in {selected_year}: **{correlatie:.2f}** "
            "(1,0 is een perfect positief verband, 0 is geen verband, -1,0 is een perfect omgekeerd verband). "
            "Onderzoekt of er bewijs is voor een Environmental Kuznets Curve: stijgt CO2-uitstoot mee met GDP "
            "tot een bepaald niveau, om daarna af te vlakken of te dalen?"
        )

        fig_ekc = px.scatter(
            df_ekc_clean,
            x="gdp_per_capita",
            y="co2_per_capita",
            size="population",
            color="income_group",
            hover_name="country",
            log_x=use_log_scale,
            trendline="ols",
            trendline_scope="overall",
            trendline_color_override="#4a3aa7",
            labels=LABELS,
            title=f"GDP versus CO2-uitstoot: correlatie {correlatie:.2f} ({selected_year})",
        )
        for spoor in fig_ekc.data:
            if spoor.name == "Overall Trendline":
                spoor.name = "Trendlijn (alle landen)"
        st.plotly_chart(fig_ekc, use_container_width=True)

    st.markdown(
        "**Wat valt op:** lage-inkomenslanden laten meestal zowel een lage CO2-uitstoot "
        "als een laag GDP zien. Opkomende economieën laten vaak de sterkste stijging in "
        "CO2-uitstoot zien naarmate industrie en economie groeien. Bij hoge-inkomenslanden "
        "zie je meer spreiding: sommige slagen erin hun uitstoot per inwoner af te vlakken "
        "of te verlagen, ook wel groene ontkoppeling genoemd. De paarse lijn is de trendlijn "
        "over alle landen heen (een eenvoudige lineaire regressie)."
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

    st.subheader("Eén land tegen de rest: wie loopt voor, wie loopt achter?")
    st.caption(
        "Kies een hoofdland (kleur, dik, ondoorzichtig) en eventueel vergelijkingslanden "
        "(grijs, dun, transparant) om te zien hoe het hoofdland zich verhoudt tot de rest, "
        "zonder dat de vergelijkingslanden het beeld overnemen."
    )

    kol_a, kol_b = st.columns([1, 1])
    with kol_a:
        gekozen_land = st.selectbox(
            "Hoofdland",
            landen_lijst,
            index=landen_lijst.index("Netherlands") if "Netherlands" in landen_lijst else 0,
        )
    with kol_b:
        standaard_vergelijking = [l for l in ["Germany", "China", "United States"] if l in landen_lijst and l != gekozen_land]
        vergelijkingslanden = st.multiselect(
            "Vergelijkingslanden (optioneel, max 5)",
            options=[l for l in landen_lijst if l != gekozen_land],
            default=standaard_vergelijking[:3],
            max_selections=5,
        )

    metric_keuze = st.radio(
        "Welke indicator wil je vergelijken?",
        options=["co2_per_capita", "renewables_share_elec"],
        format_func=lambda x: LABELS[x],
        horizontal=True,
    )

    fig_vergelijk = go.Figure()

    # We tekenen de context eerst (grijs, dun, transparant), zodat de
    # hoofdlijn er straks bovenop komt te liggen in plaats van andersom.
    for land in vergelijkingslanden:
        df_context = df[df["country"] == land].sort_values("year")
        fig_vergelijk.add_trace(go.Scatter(
            x=df_context["year"], y=df_context[metric_keuze],
            mode="lines", name=land,
            line=dict(color=KLEUR_CONTEXT, width=1.5),
            opacity=0.55,
        ))

    # Het hoofdland tekenen we als laatste: kleur, dik, vol.
    df_hoofd = df[df["country"] == gekozen_land].sort_values("year")
    fig_vergelijk.add_trace(go.Scatter(
        x=df_hoofd["year"], y=df_hoofd[metric_keuze],
        mode="lines+markers", name=gekozen_land,
        line=dict(color=KLEUR_HOOFDROL, width=3.5),
    ))

    fig_vergelijk.add_vline(x=2015, line_dash="dot", line_color="blue", annotation_text="Klimaatakkoord van Parijs (2015)")
    fig_vergelijk.update_layout(
        title=f"{gekozen_land} ten opzichte van {len(vergelijkingslanden)} andere landen: {LABELS[metric_keuze]}",
        xaxis_title=LABELS["year"],
        yaxis_title=LABELS[metric_keuze],
        legend_title=LABELS["country"],
    )

    if df_hoofd[metric_keuze].dropna().empty:
        st.warning(f"Er is geen data beschikbaar voor {gekozen_land} op deze indicator.")
    else:
        st.plotly_chart(fig_vergelijk, use_container_width=True)

    st.divider()

    st.subheader(f"Jaar-op-jaar verandering in CO2-uitstoot: {gekozen_land}")
    st.caption(
        "In plaats van alleen het niveau te tonen, laat deze grafiek zien hoeveel de CO2-uitstoot per "
        "inwoner elk jaar steeg of daalde ten opzichte van het jaar ervoor (berekend met .diff())."
    )

    df_hoofd_diff = df_hoofd.dropna(subset=["co2_verandering"])
    if df_hoofd_diff.empty:
        st.warning(f"Er is niet genoeg opeenvolgende data voor {gekozen_land} om jaar-op-jaar verandering te tonen.")
    else:
        fig_diff = px.bar(
            df_hoofd_diff,
            x="year",
            y="co2_verandering",
            labels=LABELS,
            title=f"Jaar-op-jaar verandering in CO2 per inwoner: {gekozen_land}",
            color=df_hoofd_diff["co2_verandering"] > 0,
            color_discrete_map={True: "#e34948", False: "#1baf7a"},
        )
        fig_diff.update_layout(showlegend=False)
        fig_diff.update_traces(hovertemplate="Jaar: %{x}<br>Verandering: %{y:.2f} ton<extra></extra>")
        fig_diff.add_hline(y=0, line_color="gray")

        # We annoteren de grootste stijging en de grootste daling.
        grootste_stijging = df_hoofd_diff.loc[df_hoofd_diff["co2_verandering"].idxmax()]
        grootste_daling = df_hoofd_diff.loc[df_hoofd_diff["co2_verandering"].idxmin()]
        fig_diff.add_annotation(
            x=grootste_stijging["year"], y=grootste_stijging["co2_verandering"],
            text="grootste stijging", showarrow=True, arrowhead=2, ay=-30,
        )
        fig_diff.add_annotation(
            x=grootste_daling["year"], y=grootste_daling["co2_verandering"],
            text="grootste daling", showarrow=True, arrowhead=2, ay=30,
        )
        st.plotly_chart(fig_diff, use_container_width=True)

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
    st.write("- Software: Python, Streamlit, Pandas, Plotly Express, Kagglehub, Statsmodels (trendlijn)")

    st.write("**Voorbeeld van de samengevoegde data:**")
    preview_cols = ["iso_code", "country", "year", "co2_emissions", "co2_per_capita", "renewables_share_elec", "gdp_per_capita", "income_group"]
    st.dataframe(df_year[preview_cols].rename(columns=LABELS).head(15))

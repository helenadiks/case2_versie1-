# Documentatie & Toelichting Streamlit Dashboard: Klimaatbeleid vs. Realiteit

## 1. Introductie & Koppeling met de Opdracht

Dit dashboard is gebouwd in Python met **Streamlit**, **Pandas**, **Plotly Express** en **Kagglehub**. Het doel is om data over CO₂-uitstoot te combineren met data over hernieuwbare energie om te onderzoeken of de klimaattransitie daadwerkelijk leidt tot lagere emissies, en welke rol economische welvaart hierin speelt.

### Aansluiting op de onderzoeksvragen

* **Hoofdvraag:** *"In hoeverre komt de transitie naar hernieuwbare energie daadwerkelijk tot uiting in dalende CO₂-uitstoot, en hoe verhoudt dit zich tot het inkomensniveau van landen?"*
$\rightarrow$ **Oplossing in app:** De gebruiker kan via de zijbalk jaartallen, landen en inkomensniveaus filteren, terwijl KPI-kaarten en visualisaties direct inzicht geven in deze dynamiek.
* **Deelvraag 1 ("Walk vs. Talk"):** *"Welke landen laten een reële ontkoppeling zien en welke blijven steken?"*
$\rightarrow$ **Oplossing in app:** het tabblad **"Walk vs. talk"** berekent de verandering over de gehele periode en deelt landen in vier categorieën in op een scatterplot met scheidingslijnen.
* **Deelvraag 2 & 3 (Environmental Kuznets Curve & inkomensgroepen):** *"Is er bewijs voor een Environmental Kuznets Curve en hoe verschilt dit per inkomensgroep?"*
$\rightarrow$ **Oplossing in app:** het tabblad **"CO2 vs. welvaart"** plot het GDP per inwoner tegen de CO₂-uitstoot per inwoner, waarbij landen gekleurd zijn op basis van hun inkomensgroep.
* Het tabblad **"Kaart en tijdlijn"** is geen aparte deelvraag, maar levert aanvullend bewijs: geografische spreiding en verloop per land.
* Het tabblad **"Data en methode"** licht de databronnen, opschoning en samenvoeging toe (transparantie/methodologie).

**Let op:** in de app zelf staat nergens letterlijk "Deelvraag 1" of "Deelvraag 2 & 3" — de tabbladen hebben een beschrijvende titel, met de onderzoeksvraag als kleinere toelichting eronder. Dat is bewust gedaan om het dashboard prettiger leesbaar en professioneler te maken voor een buitenstaander.

---

## 2. Stap-voor-Stap Code-Uitleg

### Stap 1: Imports & Pagina-instellingen

```python
import glob
import os

import streamlit as st
import pandas as pd
import plotly.express as px
import kagglehub

st.set_page_config(page_title="Klimaatbeleid vs. realiteit", layout="wide")
```

* **Wat gebeurt hier?**
De benodigde bibliotheken worden geladen, inclusief `kagglehub` voor het rechtstreeks ophalen van de datasets van Kaggle. `st.set_page_config` zet de titel van het browsertabblad en stelt de lay-out in op `wide`.

---

### Stap 2: Vaste labels voor weergave

```python
LABELS = {
    "co2_per_capita": "CO2 per inwoner (ton)",
    "renewables_share_elec": "Aandeel hernieuwbare stroom (%)",
    "gdp_per_capita": "GDP per inwoner (USD)",
    ...
}
```

* **Wat gebeurt hier?**
Eén centrale dictionary vertaalt elke technische kolomnaam (die in de data onderling met underscores geschreven is, zoals `co2_per_capita`) naar een nette, leesbare tekst zonder underscores. Deze dictionary wordt bij elke grafiek als `labels=` meegegeven, zodat assen, legenda's en tabelkoppen overal consistent en professioneel ogen.

---

### Stap 3: Data ophalen, opschonen en samenvoegen

```python
@st.cache_data
def load_data():
    co2_path = kagglehub.dataset_download("vishnupriyan123/annual-co2-emissions-per-country")
    ren_path = kagglehub.dataset_download("elvisbui/renewable-energy-share-by-country-2000-2025")
    ...
```

* **Wat gebeurt hier?**
1. **Ophalen via Kagglehub:** in plaats van handmatig gedownloade CSV-bestanden in een lokale map te lezen, worden de datasets rechtstreeks via de Kaggle API opgehaald. Dit vereist een geldige Kaggle API-sleutel op het systeem (`~/.kaggle/kaggle.json`).
2. **Caching (`@st.cache_data`):** zorgt dat de download en verwerking maar één keer gebeurt, niet bij elke interactie met een filter.
3. **Kolomhernoeming:** kolomnamen in de CO₂-dataset worden meteen na het inladen gestandaardiseerd (`Entity` → `country`, `Code` → `iso_code`, `Year` → `year`, `Annual CO₂ emissions` → `co2_emissions`), zodat ze matchen met de structuur van de energie-dataset. Dit gebeurt bewust direct na het inladen, in plaats van pas later in losse grafieken, zoals ook in het hoorcollege werd aangeraden.
4. **Opschonen (ISO3-filtering):** met `df['iso_code'].str.len() == 3` worden alleen rijen met een geldige 3-letterige landcode behouden. Regio's, werelddelen en totalen (zoals *World* of *Europe*) worden hiermee uitgesloten.
5. **Antarctica verwijderen:** Antarctica heeft toevallig wél een geldige 3-letterige code (`ATA`) en overleefde daardoor de ISO3-filter, maar heeft geen bevolkings- of GDP-cijfers. Per-inwoner-berekeningen zijn daardoor niet zinvol, dus deze rijen worden er apart uitgehaald.
6. **Kolomnaam-botsing oplossen:** beide datasets bevatten een kolom `country` (die geen join-sleutel is). Zonder ingrijpen zou de merge automatisch `country_x` en `country_y` maken. De `country`-kolom uit de renewable-dataset wordt daarom vóór het samenvoegen verwijderd, zodat de landnaam uit de CO₂-dataset leidend blijft.
7. **Inner join:** de datasets worden samengevoegd op de sleutel `[iso_code, year]`.
8. **Feature engineering (nieuwe variabelen):**
   * `gdp_per_capita` = GDP gedeeld door bevolking (veilig berekend, geeft `None` bij ontbrekende of nul-bevolking).
   * `co2_per_capita` = CO₂-uitstoot gedeeld door bevolking.
   * `income_group` = landen worden ingedeeld in drie klassen met `pd.cut()`: *Lage inkomens* (< $5.000), *Opkomende inkomens* ($5.000–$20.000), *Hoge inkomens* (> $20.000). Landen zonder GDP-data krijgen de aparte categorie *"Onbekend / geen GDP-data"*, in plaats van dat ze uit de dataset verdwijnen — zo blijven ze zichtbaar op de kaart en in de tijdlijn, en vallen ze alleen weg uit de welvaart-analyse waar een GDP-waarde vereist is.
9. **Statistieken bijhouden:** aantallen rijen vóór en na opschoning, en het aantal landen zonder GDP-data, worden opgeslagen in `stats` voor verantwoording in het tabblad "Data en methode".

---

### Stap 4: Zijbalk & dynamische filters

```python
st.sidebar.header("Filters")
selected_year = st.sidebar.slider("Selecteer een jaar", ...)
selected_countries = st.sidebar.multiselect("Filter op specifieke landen", ...)
selected_income = st.sidebar.selectbox("Filter op inkomensniveau", ...)
use_log_scale = st.sidebar.checkbox("Logaritmische schaal voor GDP", ...)
```

* **Wat gebeurt hier?**
De zijbalk bevat vier interactieve elementen: een **jaar-slider**, een **landenfilter** (multiselect), een **inkomensgroep-dropdown**, en een **checkbox** voor een logaritmische GDP-as (zodat grote verschillen tussen arme en rijke landen overzichtelijk blijven). Deze filters werken door op alle tabbladen die per jaar of per land filteren.

---

### Stap 5: Kerncijfers (KPI's)

```python
col1, col2, col3, col4 = st.columns(4)
col1.metric("Aantal geanalyseerde landen", len(df_year))
...
```

* **Wat gebeurt hier?**
Bovenaan het dashboard tonen vier kaarten samenvattende cijfers, die live meerekenen met de gekozen filters.

---

### Stap 6: Tabblad "Walk vs. talk"

```python
def categoriseer(row):
    if row['ren_diff'] > 5 and row['co2_pct_change'] < 0:
        return 'Walk: groene daling ...'
    ...
```

* **Wat gebeurt hier?**
Vergelijkt het eerste jaar (2000) met het laatste jaar (2022) per land: hoeveel procentpunt is het aandeel hernieuwbare energie gestegen, en hoeveel procent is de CO₂-uitstoot per inwoner veranderd? Landen worden via de functie `categoriseer()` in vier kwadranten ingedeeld en getoond in een scatterplot met referentielijnen. De titel van dit tabblad benoemt geen letterlijk deelvraagnummer, maar stelt de vraag direct: *"Praat een land de talk, of loopt het ook de walk?"*

---

### Stap 7: Tabblad "CO2 vs. welvaart"

```python
fig_ekc = px.scatter(df_ekc_clean, x="gdp_per_capita", y="co2_per_capita", size="population", color="income_group", ...)
```

* **Wat gebeurt hier?**
Een scatterplot toont het verband tussen welvaart (x-as) en CO₂-uitstoot (y-as) voor het gekozen jaar. Bolgrootte staat voor bevolkingsomvang, kleur voor inkomensgroep. Doel: zichtbaar maken of rijkere landen minder uitstoten per inwoner (de Environmental Kuznets Curve).

---

### Stap 8: Tabblad "Kaart en tijdlijn"

```python
fig_map = px.choropleth(df_year, locations="iso_code", color="renewables_share_elec", ...)
fig_line = px.line(df_land, x="year", y=["renewables_share_elec", "co2_per_capita"], ...)
```

* **Wat gebeurt hier?**
1. **Wereldkaart:** kleurt landen op basis van hun aandeel hernieuwbare stroom in het gekozen jaar.
2. **Tijdlijn per land:** een selectiebox laat de gebruiker één land kiezen (standaard Nederland); een lijngrafiek toont het verloop door de jaren heen, met een stippellijn bij 2015 (Klimaatakkoord van Parijs) als referentiepunt.

---

### Stap 9: Tabblad "Data en methode"

```python
st.write(f"- Samengevoegde dataset: {stats['merged']:,} rijen, {stats['totaal_landen']} landen")
st.info(f"{stats['landen_zonder_gdp']} van de {stats['totaal_landen']} landen missen GDP-data ...")
st.dataframe(df_year[preview_cols].rename(columns=LABELS).head(15))
```

* **Wat gebeurt hier?**
Dit tabblad biedt transparantie: hoeveel rijen er in de ruwe data zaten, hoeveel er overbleven na opschoning, hoeveel landen GDP-data missen en wat dat betekent voor de analyse, plus een voorbeeldweergave van de samengevoegde tabel met nette (niet-technische) kolomnamen.

---

## 3. Samenvatting van de Technische Werking

| Component | Gebruikte Technologie | Functie in de App |
| --- | --- | --- |
| **Data ophalen** | `kagglehub` | Downloadt de datasets rechtstreeks via de Kaggle API. |
| **Data structuur** | `pandas.DataFrame` | Opschonen, joins, berekeningen (`gdp_per_capita`, `income_group`). |
| **Performance** | `@st.cache_data` | Voorkomt herhaaldelijk downloaden/inlezen van bestanden. |
| **Interactiviteit** | `st.sidebar`, `st.slider`, `st.multiselect`, `st.selectbox` | Dynamisch filteren van de gegevens. |
| **Visualisatie** | `plotly.express` (Scatter, Line, Choropleth) | Interactieve en zoombare grafieken en wereldkaarten. |
| **Leesbaarheid** | Centrale `LABELS`-dictionary | Zorgt dat titels, assen en tabelkoppen nergens technische kolomnamen tonen. |
| **Structuur** | `st.tabs`, `st.columns`, `st.metric` | Overzichtelijke en nette presentatie van de resultaten. |

---

## 4. Bekende keuzes & beperkingen

* **Antarctica** is bewust uitgesloten (geen bevolkings-/GDP-data, per-inwoner-cijfers zijn er niet zinvol).
* **Kosovo** ontbreekt in de dataset: de dataset codeert Kosovo als `OWID_KOS`, wat door de ISO3-lengtefilter (precies 3 letters) wordt gezien als een niet-standaard code en dus wordt uitgesloten, samen met echte aggregaten zoals "World".
* **41 van de 205 landen** missen GDP-data in minstens één jaar. Deze landen blijven zichtbaar op de kaart en in de tijdlijn, maar vallen weg uit de welvaart-analyse (tabblad "CO2 vs. welvaart").
* Extreme waarden zoals 100% hernieuwbare stroom (bijvoorbeeld Albanië) zijn gecontroleerd en kloppen: dit zijn landen die hun elektriciteit vrijwel volledig uit waterkracht halen, geen fout in de data.

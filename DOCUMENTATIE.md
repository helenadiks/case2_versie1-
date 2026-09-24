[DOCUMENTATIE-7.md](https://github.com/user-attachments/files/32601457/DOCUMENTATIE-7.md)

# Documentatie & Toelichting Streamlit Dashboard: Transitie en Uitstoot

## 1. Introductie & Koppeling met de Opdracht

Dit dashboard is gebouwd in Python met **Streamlit**, **Pandas**, **Plotly** en **Kagglehub**. Het doel is om data over CO₂-uitstoot te combineren met data over hernieuwbare energie om te onderzoeken of de klimaattransitie daadwerkelijk leidt tot lagere emissies, en welke rol economische welvaart hierin speelt.

### Aansluiting op de onderzoeksvragen

* **Hoofdvraag:** *"In hoeverre komt de transitie naar hernieuwbare energie daadwerkelijk tot uiting in dalende CO₂-uitstoot, en hoe verhoudt dit zich tot het inkomensniveau van landen?"* De gebruiker kan via de zijbalk jaartallen, landen en inkomensniveaus filteren, terwijl KPI-kaarten en visualisaties direct inzicht geven in deze dynamiek.
* **Deelvraag 1 ("Walk vs. Talk"):** *"Welke landen laten een reële ontkoppeling zien en welke blijven steken?"* Het tabblad **"Walk vs. talk"** berekent de verandering over de gehele periode en deelt landen in vier categorieën in op een scatterplot met scheidingslijnen en annotaties bij de duidelijkste voorbeelden.
* **Deelvraag 2 & 3 (Environmental Kuznets Curve & inkomensgroepen):** *"Is er bewijs voor een Environmental Kuznets Curve en hoe verschilt dit per inkomensgroep?"* Het tabblad **"CO2 vs. welvaart"** plot het GDP per inwoner tegen de CO₂-uitstoot per inwoner, met een trendlijn en het correlatiegetal, waarbij landen gekleurd zijn op basis van hun inkomensgroep.
* Het tabblad **"Kaart en tijdlijn"** is geen aparte deelvraag, maar levert aanvullend bewijs: geografische spreiding, een directe vergelijking tussen een gekozen hoofdland en andere landen, en de jaar-op-jaar verandering per land.
* Het tabblad **"Data en methode"** licht de databronnen, opschoning en samenvoeging toe (transparantie/methodologie).

**Let op:** in de app zelf staat nergens letterlijk "Deelvraag 1" of "Deelvraag 2 & 3". De tabbladen hebben een beschrijvende titel, met de onderzoeksvraag als kleinere toelichting eronder.

---

## 2. Installatie & Uitvoeren

### Lokaal draaien

1. **Vereiste packages installeren:**
   ```
   pip install -r requirements.txt
   ```
2. **Kaggle API-sleutel instellen** (nodig omdat de datasets rechtstreeks via de Kaggle API worden opgehaald, niet handmatig gedownload):
   * Log in op [kaggle.com](https://www.kaggle.com), ga naar *Account*, *API*, *Create New Token*.
   * Dit download een bestand `kaggle.json`. Zet dit bestand in de map `~/.kaggle/` (op Windows: `C:\Users\<gebruikersnaam>\.kaggle\`).
3. **App starten:**
   ```
   streamlit run app.py
   ```

### Publiceren op Streamlit Community Cloud

Dit is het onderdeel waar een groep gemakkelijk op kan stuklopen: lokaal werkt de Kaggle-sleutel via het bestand `kaggle.json`, maar dat bestand staat niet in de GitHub-repository (en hoort daar ook niet in te staan, want het is een persoonlijke sleutel). Zonder extra stap zou de gepubliceerde app dus crashen bij het opstarten.

1. Zet de repository op GitHub (zonder `kaggle.json` erin, dat is geheime informatie).
2. Maak de app aan op [share.streamlit.io](https://share.streamlit.io/) door in te loggen met je GitHub-account.
3. Ga in de app-instellingen naar **Settings > Secrets** en voeg toe:
   ```toml
   KAGGLE_USERNAME = "jouw_gebruikersnaam"
   KAGGLE_KEY = "jouw_api_key"
   ```
4. De functie `zet_kaggle_credentials_klaar()` bovenaan `app.py` leest deze secrets uit en zet ze om naar de omgevingsvariabelen die `kagglehub` verwacht. Lokaal (zonder `secrets.toml`) doet deze functie niets, en valt de app terug op het gewone `kaggle.json`-bestand.

**Controleer dit vóór het inleveren:** open de gepubliceerde link in een incognito-venster en kijk of het dashboard zonder foutmelding laadt. Dit is de eis *"een schone clone van de repo draait zonder handmatige stappen"*, met een aftrek van 1,0 op beide cijfers als dit niet werkt.

---

## 3. Belangrijkste Inzichten

Deze bevindingen komen rechtstreeks uit de samengevoegde dataset (2000-2022, 205 landen) en staan ook zichtbaar in de app zelf (niet alleen hier):

* **Walk vs. talk:** van de 198 landen met volledige data voor beide jaren, combineert slechts **25% (49 landen)** een stijging in hernieuwbare energie mét een daling van de CO₂-uitstoot per inwoner. **Aruba** laat de sterkste ontkoppeling zien; **Cambodja** is het duidelijkste voorbeeld van een land waar hernieuwbare energie fors toenam, maar de CO₂-uitstoot per inwoner toch met meer dan 600% steeg (waarschijnlijk doordat de totale energievraag veel harder groeide dan de omschakeling naar hernieuwbaar).
* **Kuznets-curve:** in 2022 is de correlatie tussen GDP per inwoner en CO₂-uitstoot per inwoner **0,77** (sterk positief), zichtbaar via de trendlijn in het dashboard zelf. Landen met een GDP per inwoner onder de mediaan stoten gemiddeld **1,24 ton** CO₂ per inwoner uit, tegenover **7,63 ton** bij landen boven de mediaan. Er is in deze data dus geen bewijs dat CO₂-uitstoot per inwoner weer daalt bij de hoogste inkomens (het "omgekeerde-U"-patroon van de klassieke Kuznets-curve).

---

## 4. Stap-voor-Stap Code-Uitleg

### Stap 1: Imports & Pagina-instellingen

```python
import glob, os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import kagglehub

st.set_page_config(page_title="Transitie en uitstoot: houdt het gelijke tred?", layout="wide")
```

* **Wat gebeurt hier?**
Naast `plotly.express` (voor de meeste grafieken) wordt ook `plotly.graph_objects` geladen. Dat is nodig voor de vergelijkingsgrafiek in tabblad 3, waar elke lijn een eigen kleur, dikte en doorzichtigheid nodig heeft. Dat kan `plotly.express` niet per lijn apart instellen, `graph_objects` wel.

---

### Stap 2: Kaggle-authenticatie (lokaal én op Streamlit Cloud)

```python
def zet_kaggle_credentials_klaar():
    try:
        if "KAGGLE_USERNAME" in st.secrets and "KAGGLE_KEY" in st.secrets:
            os.environ["KAGGLE_USERNAME"] = st.secrets["KAGGLE_USERNAME"]
            os.environ["KAGGLE_KEY"] = st.secrets["KAGGLE_KEY"]
    except Exception:
        pass

zet_kaggle_credentials_klaar()
```

* **Wat gebeurt hier?**
`kagglehub` heeft ergens een Kaggle API-sleutel nodig om datasets te downloaden. Deze functie checkt of die sleutel als Streamlit-secret is ingesteld (voor de gepubliceerde versie) en zet die dan om naar omgevingsvariabelen. Lokaal, waar meestal al een `kaggle.json`-bestand op de standaardlocatie staat, doet deze functie niets schadelijks: de `try/except` vangt af dat er (nog) geen `secrets.toml` bestaat.

---

### Stap 3: Data ophalen, opschonen en samenvoegen

* **Kolomhernoeming** direct na het inladen (`Entity` wordt `country`, `Code` wordt `iso_code`, enzovoort), zoals ook in het hoorcollege werd aangeraden.
* **ISO3-filtering:** alleen rijen met een geldige 3-letterige landcode blijven over, wat automatisch regio's en werelddelen uitsluit.
* **Antarctica** wordt apart verwijderd (heeft wél een geldige code, maar geen bevolkings- of GDP-cijfers).
* **Kolomnaam-botsing:** beide datasets hebben een kolom `country`; die van de renewable-dataset wordt vóór de merge verwijderd, zodat er geen `country_x`/`country_y` ontstaat.
* **Inner join** op `[iso_code, year]`.
* **Nieuwe variabelen:**
  * `gdp_per_capita` en `co2_per_capita`: GDP/CO2 gedeeld door bevolking.
  * `co2_verandering`: het verschil met het jaar ervoor, berekend met **`.diff()`**, per land apart via `groupby("iso_code")`. Zonder die groepering zou de eerste rij van het ene land worden afgetrokken van de laatste rij van het vorige land, wat een onzinnige uitschieter zou opleveren.
  * `income_group`: landen ingedeeld in drie klassen met `pd.cut()`, met een aparte categorie voor landen zonder GDP-data (die blijven zo zichtbaar op de kaart en in de tijdlijn).

---

### Stap 4: Zijbalk & dynamische filters

Vier interactieve elementen: een **jaar-slider**, een **landenfilter** (multiselect), een **inkomensgroep-dropdown**, en een **checkbox** voor een logaritmische GDP-as. Dit dekt de eis van minimaal een slider, checkbox en dropdown, elk gekoppeld aan tabellen/visualisaties op meerdere tabbladen.

---

### Stap 5: Tabblad "Walk vs. talk"

```python
n_walk = (df_change["Categorie"].str.startswith("Walk")).sum()
pct_walk = round(100 * n_walk / n_totaal)
st.subheader(f"Slechts {pct_walk}% van de landen maakt de belofte van hernieuwbare energie ook echt waar")
```

* **Wat gebeurt hier?**
De titel is geen beschrijving meer ("Walk vs. talk vergelijking"), maar een bewering die rechtstreeks uit de data wordt berekend. Daarnaast worden het duidelijkste "walk"-land en het duidelijkste "talk"-land met `fig.add_annotation()` in de grafiek zelf benoemd, in plaats van dat de kijker zelf tussen alle punten moet zoeken. De y-as wordt vervolgens met `fig.update_yaxes(range=[...])` ingezoomd op basis van diezelfde twee aangewezen landen (plus 15% marge), zodat een enkele extreme uitschieter (zie sectie 6) niet de hele as openrekt en de overige landen onleesbaar maakt.

---

### Stap 6: Tabblad "CO2 vs. welvaart"

```python
correlatie = df_ekc_clean["gdp_per_capita"].corr(df_ekc_clean["co2_per_capita"])
fig_ekc = px.scatter(..., trendline="ols", trendline_scope="overall", ...)
```

* **Wat gebeurt hier?**
De correlatiecoëfficiënt wordt met `.corr()` berekend en gebruikt om automatisch een bewerende titel te kiezen ("rijkere landen stoten meer uit" versus "minder uit" versus "geen duidelijk verband", afhankelijk van het teken en de sterkte). De trendlijn (`trendline="ols"`, een eenvoudige lineaire regressie) maakt het verband ook visueel zichtbaar. Dit vereist het package `statsmodels`, dat daarom in `requirements.txt` staat.

---

### Stap 7: Tabblad "Kaart en tijdlijn": vergelijkingsgrafiek

```python
for land in vergelijkingslanden:
    fig_vergelijk.add_trace(go.Scatter(..., line=dict(color=KLEUR_CONTEXT, width=1.5), opacity=0.55))
fig_vergelijk.add_trace(go.Scatter(..., line=dict(color=KLEUR_HOOFDROL, width=3.5)))
```

* **Wat gebeurt hier?**
Dit past de techniek uit het werkcollege toe: context (de vergelijkingslanden) wordt **eerst** getekend in grijs, dun en halftransparant; het hoofdland wordt **daarna** getekend in kleur, dik en vol. Omdat Plotly lijnen tekent in de volgorde waarin ze worden toegevoegd, komt de hoofdlijn zo automatisch bovenop te liggen. De gebruiker kiest zelf het hoofdland en tot vijf vergelijkingslanden via twee `st.selectbox`/`st.multiselect`-widgets, en kan wisselen tussen CO2-uitstoot en aandeel hernieuwbare energie via een `st.radio`.

---

### Stap 8: Tabblad "Kaart en tijdlijn": jaar-op-jaar verandering

```python
fig_diff = px.bar(df_hoofd_diff, x="year", y="co2_verandering", ...)
grootste_stijging = df_hoofd_diff.loc[df_hoofd_diff["co2_verandering"].idxmax()]
grootste_daling = df_hoofd_diff.loc[df_hoofd_diff["co2_verandering"].idxmin()]
```

* **Wat gebeurt hier?**
In plaats van alleen het niveau van CO2-uitstoot te tonen, laat deze staafgrafiek de jaar-op-jaar **verandering** zien (de `co2_verandering`-kolom uit Stap 3, berekend met `.diff()`). Staven zijn rood bij een stijging en groen bij een daling. De grootste stijging en de grootste daling worden automatisch opgezocht met `.idxmax()` / `.idxmin()` en geannoteerd in de grafiek.

**Let op bij `.idxmax()`/`.idxmin()` op een kolom met NaN's:** deze functies slaan NaN-waarden stilzwijgend over. Dat is hier bewust gebruikt na een `.dropna(subset=["co2_verandering"])`, zodat het zoeken alleen over echte waarden gaat. Zou je dit toepassen op een kolom waar een deel van de NaN's er systematisch uitziet (bijvoorbeeld omdat twee reeksen niet helemaal overlappen), dan kan dit stil de verkeerde uitschieter opleveren, dus eerst `.isna().sum()` checken blijft de vuistregel.

---

### Stap 9: Tabblad "Data en methode"

Ongewijzigd ten opzichte van de vorige versie: transparantie over aantallen rijen voor/na opschoning, hoeveel landen GDP-data missen, en een voorbeeldweergave van de samengevoegde tabel met nette kolomnamen.

---

## 5. Samenvatting van de Technische Werking

| Component | Gebruikte Technologie | Functie in de App |
| --- | --- | --- |
| **Data ophalen** | `kagglehub` | Downloadt de datasets rechtstreeks via de Kaggle API. |
| **Authenticatie** | `st.secrets` + omgevingsvariabelen | Laat de app zowel lokaal als op Streamlit Cloud werken. |
| **Data structuur** | `pandas.DataFrame` | Opschonen, joins, `.diff()` voor jaar-op-jaar verandering, `.corr()` voor de correlatie. |
| **Performance** | `@st.cache_data` | Voorkomt herhaaldelijk downloaden/inlezen van bestanden. |
| **Interactiviteit** | `st.sidebar`, `st.slider`, `st.multiselect`, `st.selectbox`, `st.radio` | Dynamisch filteren en het kiezen van hoofd-/vergelijkingslanden. |
| **Visualisatie** | `plotly.express` (Scatter met trendline, Bar, Choropleth) en `plotly.graph_objects` (vergelijkingsgrafiek) | Interactieve grafieken, wereldkaart, en fijn gestuurde context-vs-hoofdrol-lijnen. |
| **Annotaties** | `fig.add_annotation()`, `fig.add_hline()`/`add_vline()` | Wijst de kijker actief op de belangrijkste punten in plaats van dat die zelf gezocht moeten worden. |
| **Leesbaarheid** | Centrale `LABELS`-dictionary | Zorgt dat titels, assen en tabelkoppen nergens technische kolomnamen tonen. |
| **Structuur** | `st.tabs`, `st.columns`, `st.metric` | Overzichtelijke en nette presentatie van de resultaten. |

---

## 6. Bekende keuzes & beperkingen

* **Antarctica** is bewust uitgesloten (geen bevolkings-/GDP-data, per-inwoner-cijfers zijn er niet zinvol).
* **Kosovo** ontbreekt in de dataset: de dataset codeert Kosovo als `OWID_KOS`, wat door de ISO3-lengtefilter (precies 3 letters) wordt gezien als een niet-standaard code en dus wordt uitgesloten, samen met echte aggregaten zoals "World".
* **41 van de 205 landen** missen GDP-data in minstens één jaar. Deze landen blijven zichtbaar op de kaart en in de tijdlijn, maar vallen weg uit de welvaart-analyse.
* Extreme waarden zoals 100% hernieuwbare stroom (bijvoorbeeld Albanië) zijn gecontroleerd en kloppen: dit zijn landen die hun elektriciteit vrijwel volledig uit waterkracht halen, geen fout in de data.
* De trendlijn in tabblad "CO2 vs. welvaart" is een eenvoudige lineaire regressie (OLS) over alle zichtbare landen. Dit toont een verband, geen causaal bewijs: het dashboard beweert nergens dat welvaart CO2-uitstoot veroorzaakt, alleen dat ze samenhangen.
* De y-as van de scatter in tabblad "Walk vs. talk" is bewust ingezoomd op basis van de twee aangewezen voorbeelden (plus marge), in plaats van op het absolute maximum van de data. Zonder deze ingreep trekt een enkel land (Laos: van 0,18 naar 3,07 ton CO2 per inwoner, een stijging van 1635%) de hele as open, waardoor de overige circa 200 landen niet meer van elkaar te onderscheiden zijn. Dit is geen foute data: de procentuele uitschieter ontstaat doordat de CO2-uitstoot per inwoner in het startjaar bijna nul was, niet doordat de werkelijke stijging extreem was. Het land valt hierdoor buiten beeld van de grafiek, wat expliciet in een tekstregel onder de grafiek wordt vermeld, met de suggestie om op dat land te filteren voor het exacte cijfer.

---

## 7. Gebruikte externe code en bronnen

Het dashboard is zelf geschreven en aangepast op onze eigen samengevoegde dataset (eigen kolomnamen, eigen labels, eigen combinatie van grafieken). Een aantal standaardpatronen is overgenomen uit de officiële documentatie van de gebruikte libraries. Die patronen staan hieronder met bron, zodat na te gaan is wat ervandaan komt en wat zelf is opgezet.

* **`st.cache_data`** om de data maar één keer op te halen en niet bij elke filterwijziging opnieuw te downloaden. Patroon uit de Streamlit-documentatie over caching: [https://docs.streamlit.io/develop/concepts/architecture/caching](https://docs.streamlit.io/develop/concepts/architecture/caching). Aangepast aan onze eigen `load_data()`-functie, die twee Kaggle-datasets ophaalt, opschoont en samenvoegt.
* **`st.secrets`** om Kaggle-inloggegevens veilig in te stellen op Streamlit Community Cloud, zonder een `kaggle.json`-bestand in de repository te zetten. Patroon uit de Streamlit-documentatie over secrets management: [https://docs.streamlit.io/develop/concepts/connections/secrets-management](https://docs.streamlit.io/develop/concepts/connections/secrets-management). Zelf uitgebreid met een `try/except`, zodat de app ook lokaal blijft werken zonder een `secrets.toml`.
* **`kagglehub.dataset_download()`** om de datasets programmatisch op te halen bij Kaggle in plaats van handmatig te downloaden. Patroon uit de kagglehub-documentatie: [https://github.com/Kaggle/kagglehub](https://github.com/Kaggle/kagglehub). Zelf aangepast: de teruggegeven map wordt doorzocht op het csv-bestand met `glob`, en de kolomnamen worden direct daarna hernoemd naar onze eigen namen.
* **`trendline="ols"`** in de scatterplot van tabblad "CO2 vs. welvaart" om een trendlijn en R-waarde te berekenen. Patroon uit de Plotly Express-documentatie over trendlines: [https://plotly.com/python/linear-fits/](https://plotly.com/python/linear-fits/). Hiervoor is `statsmodels` nodig (zie `requirements.txt`). Zelf aangepast: de berekende correlatie wordt gebruikt om de titel van de grafiek automatisch te laten meebewegen.
* **`go.Figure` met losse `add_trace`-aanroepen** voor de vergelijkingsgrafiek (hoofdland versus vergelijkingslanden) in tabblad "Kaart en tijdlijn", zodat elke lijn een eigen kleur, dikte en doorzichtigheid kan krijgen. Patroon uit de Plotly-documentatie over graph objects: [https://plotly.com/python/graph-objects/](https://plotly.com/python/graph-objects/). De volgorde waarin de lijnen worden getekend (grijze vergelijkingslanden eerst, het gekleurde hoofdland als laatste erbovenop) komt uit het hoorcollege Visual Analytics over het onderscheid tussen context en hoofdrol in een grafiek, niet uit externe documentatie.

Geen van deze stukken is een compleet voorbeelddashboard dat is overgenomen; het gaat steeds om één functie of parameter uit de officiële documentatie, ingebouwd in onze eigen `load_data()`-functie en onze eigen grafieken. De groep kan bij elk van deze punten uitleggen wat de code doet en waarom die keuze is gemaakt (zie sectie 4, Stap-voor-Stap Code-Uitleg).


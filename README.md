# 🌍 Klimaatbeleid vs. Realiteit: Dashboard

Een interactief Streamlit-dashboard dat onderzoekt in hoeverre de wereldwijde transitie naar hernieuwbare energie daadwerkelijk leidt tot een lagere $\text{CO}_2$-uitstoot per inwoner, en hoe deze relatie beïnvloed wordt door de economische welvaart van landen.

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.25+-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-Express-3F4F75?style=flat&logo=plotly&logoColor=white)

---

## 📌 Onderzoeksvraag

> *"In hoeverre komt de transitie naar hernieuwbare energie daadwerkelijk tot uiting in dalende $\text{CO}_2$-uitstoot, en hoe verhoudt dit zich tot het inkomensniveau van landen?"*

---

## 📊 Functionaliteiten

Het dashboard doorloopt de analyse in vier interactieve tabs:

1. **Walk vs. Talk (Analyse van beloftes):**
   * Vergelijkt de toename van hernieuwbare energie met de werkelijke verandering in $\text{CO}_2$-uitstoot per inwoner tussen het begin- en eindjaar in de dataset.
   * Categoriseert landen in 4 groepen: *Groene daling*, *Talk (stijgende uitstoot ondanks hernieuwbare groei)*, *Passieve daling*, en *Achterblijvers*.
2. **$\text{CO}_2$ vs. Welvaart:**
   * Toetst de **Environmental Kuznets Curve (EKC)**-hypothese: stijgt de uitstoot mee met de welvaart (GDP per inwoner) om daarna af te vlakken of te dalen (groene ontkoppeling)?
   * Biedt een dynamische weergave per inkomensgroep met optionele logaritmische schaal.
3. **Kaart en Tijdlijn:**
   * **Choropleth Landkaart:** Geografische spreiding van het aandeel hernieuwbare energie per selecteerbaar jaar.
   * **Tijdreeks per land:** Historische ontwikkeling van individuele landen, inclusief markering van het *Klimaatakkoord van Parijs (2015)*.
4. **Data & Methode:**
   * Transparante verantwoording van het opschoningsproces, koppelingsstatistieken, afhandeling van ontbrekende data en een datapreview.

---

## 📂 Data & Methodologie

De data wordt bij het opstarten automatisch opgehaald via de `kagglehub` API en gecombineerd uit twee bronnen ( Our World in Data / Ember / Energy Institute):
* **Annual $\text{CO}_2$ Emissions per Country** (`vishnupriyan123/annual-co2-emissions-per-country`)
* **Renewable Energy Share by Country (2000-2025)** (`elvisbui/renewable-energy-share-by-country-2000-2025`)

### Data-opschoning:
* **ISO3 Filtering:** Alleen geldige 3-letterige landcodes worden meegenomen om aggregaten (zoals continenten of wereldelementen) uit te sluiten.
* **Antarctica (ATA):** Expliciet verwijderd vanwege het ontbreken van vaste inwoners en economische data.
* **Merge:** Inner join op basis van `iso_code` en `year`.
* **Afgeleide variabelen:** Berekent $\text{CO}_2$ per inwoner, GDP per inwoner en deelt landen in op basis van World Bank-inkomensgroepen.

---

## 🛠️ Installatie & Gebruik

### Prerequisites

Zorg ervoor dat je Python 3.9+ geïnstalleerd hebt.

### 1. Repository klonen
```bash
git clone [https://github.com/jouw-gebruikersnaam/klimaatbeleid-vs-realiteit.git](https://github.com/jouw-gebruikersnaam/klimaatbeleid-vs-realiteit.git)
cd klimaatbeleid-vs-realiteit

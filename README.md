[README.md](https://github.com/user-attachments/files/32601700/README.md)

# 🌍 Transitie en uitstoot: houdt het gelijke tred?

Een interactief Streamlit-dashboard dat onderzoekt in hoeverre de transitie naar hernieuwbare energie daadwerkelijk tot uiting komt in dalende CO2-uitstoot, en hoe dit zich verhoudt tot het inkomensniveau van landen.

## Wat kun je bekijken?

* **Walk vs. talk**: welke landen combineren een groei in hernieuwbare energie ook echt met een daling van hun CO2-uitstoot per inwoner, en welke landen praten er wel over maar doen het niet.
* **CO2 vs. welvaart**: de relatie tussen GDP per inwoner en CO2-uitstoot per inwoner, met een trendlijn en de berekende correlatie.
* **Kaart en tijdlijn**: geografische verdeling van hernieuwbare energie, plus een vergelijking van een zelf gekozen hoofdland tegen andere landen over tijd.
* **Data en methode**: gebruikte datasets, opschoonstappen en bronnen.

Het dashboard heeft filters voor jaar, land en inkomensgroep, en per tabblad extra bediening zoals een dropdown voor het hoofdland en een keuze tussen indicatoren.

## Technologie

* Python
* Streamlit
* Pandas
* Plotly Express
* Kagglehub
* Statsmodels (voor de trendlijn)

De data wordt automatisch opgehaald via de Kaggle API, er staan geen csv-bestanden in deze repository.

## Live versie

https://case2team4.streamlit.app/

## Databronnen

* CO2-uitstoot per land: Kaggle, gebaseerd op Our World in Data
* Hernieuwbare energie per land: Kaggle, gebaseerd op Our World in Data, Ember en Energy Institute

De datasets worden gekoppeld op ISO3-landcode en jaar.

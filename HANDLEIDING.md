# De filmdemo lokaal uitvoeren

Je kunt [demo.html](demo.html) zonder installatie bekijken. Deze handleiding is voor wie databases, zoekindexen en lokale modelaanroepen zelf wil uitvoeren. Werk vanuit de projectmap; de terminalvoorbeelden gebruiken PowerShell op Windows.

## Eerst: de projectmap openen

Download op GitHub via **Code → Download ZIP** en pak het bestand uit, of clone de
repository met je eigen Git-URL. Open de uitgepakte map in Verkenner. Klik in de
adresbalk, typ `powershell` en druk op Enter. Je terminal staat dan in de map met
`README.md`, `demo.ipynb` en `requirements.txt`. Gebruik die map voor alle opdrachten.
Een notebookeditor zoals Visual Studio Code met de Jupyter-extensie kan het notebook
openen; voor alleen uitvoeren volstaat ook het terminalcommando uit hoofdstuk 6.

## 1. PostgreSQL en pgAdmin

Installeer PostgreSQL via de [officiële Windows-downloadpagina](https://www.postgresql.org/download/windows/). Die installer bevat ook pgAdmin; [pgAdmin is afzonderlijk beschikbaar](https://www.pgadmin.org/download/). De geteste combinatie is PostgreSQL 18.6 en pgAdmin 9.18.

1. Kies bij installatie een eigen beheerderswachtwoord en noteer de serverpoort. De geteste demo gebruikt **5433**; een standaardinstallatie kan **5432** gebruiken. Gebruik overal de werkelijk ingestelde poort.
2. Registreer de lokale server in pgAdmin met `localhost`, die poort en je beheeraccount. De eerste verbinding mag naar onderhoudsdatabase `postgres` wijzen.
3. Maak onder **Login/Group Roles** de aparte loginrol `film_demo_owner`. Stel via de definitie een eigen wachtwoord in en zet aanmelden aan. Superuserrechten zijn voor de demorol niet nodig.
4. Maak onder **Databases** de lege database **`film_demo`**, met `film_demo_owner` als eigenaar. Gebruik deze uitsluitend voor de demo.
5. Registreer in pgAdmin een tweede verbinding naar dezelfde server, nu met login `film_demo_owner` en diens wachtwoord. Open vanuit die verbinding het Query Tool op `film_demo`, zodat ook de geïmporteerde tabellen van de demorol worden. Controleer de selectie:

```sql
SELECT current_database(), current_user;
```

Verwacht database `film_demo` en gebruiker `film_demo_owner`.

Open via **Open File** [sql/laden.sql](sql/laden.sql) en voer het hele script uit. Het bevat schema, constraints, invoer en `ANALYZE` voor actuele plannerstatistieken. De databasecontrole vooraan weigert uitvoering op een anders genoemde database. Controleer de aantallen:

```sql
SELECT 'person' AS tabel, count(*) AS aantal FROM person
UNION ALL SELECT 'movie', count(*) FROM movie
UNION ALL SELECT 'acted_in', count(*) FROM acted_in;
```

Verwacht **4, 4 en 7**. Open vervolgens [queries/collegas.sql](queries/collegas.sql) in hetzelfde Query Tool. Gebruik dat centrale bestand; verwacht `P28, Amir`. Kies **Explain Analyze** of zet `EXPLAIN (ANALYZE, BUFFERS)` vóór dezezelfde query. `ANALYZE` voert de leesquery werkelijk uit. Inspecteer scans, joins, werkelijke rijen en lussen. Bij kleine tabellen hoeft de planner geen indexscan te kiezen.

## 2. Neo4j Desktop

Installeer [Neo4j Desktop via de officiële downloadpagina](https://neo4j.com/download/). De geteste combinatie is Desktop 2.2.1 met **Neo4j Enterprise 2026.10.1**. Deze route gebruikt afzonderlijke databases en rollen en vereist Enterprise.

Maak indien nodig een nieuwe lokale instance in Desktop. Je kunt ook een bestaande, expliciet voor demonstraties bedoelde lokale instance gebruiken. Noteer eigen beheeraccount, wachtwoord en Bolt-poort. Start de instance en open de queryomgeving.

1. Selecteer eerst database **`system`** en voer uit:

```cypher
CREATE DATABASE `film-demo` IF NOT EXISTS WAIT;
```

2. Selecteer daarna expliciet **`film-demo`** in de databaseselectie. Importeer niet in standaarddatabase `neo4j`. Controleer in Desktop of de demodatabase online is.
3. Open [cypher/laden.cypher](cypher/laden.cypher). Voer de afzonderlijke statements na elkaar uit: twee constraints, personen, films en relaties. Een statement eindigt met een puntkomma. Houd de databasekeuze op `film-demo`.
4. Controleer met drie losse leesqueries:

```cypher
MATCH (p:Person) RETURN count(p) AS personen;
```

```cypher
MATCH (m:Movie) RETURN count(m) AS films;
```

```cypher
MATCH ()-[r:ACTED_IN]->() RETURN count(r) AS castrelaties;
```

Verwacht **4, 4 en 7**. Bekijk de volledige graaf met:

```cypher
MATCH (p:Person)-[r:ACTED_IN]->(m:Movie) RETURN p, r, m;
```

Open [queries/collegas.cypher](queries/collegas.cypher), voer dit centrale querybestand uit en verwacht `P28, Amir`. Zet `PROFILE` vóór dezelfde query voor het werkelijke uitvoeringsplan. Inspecteer beginpunt, relatie-uitbreiding, ontdubbelen en sorteren. DB hits zijn geen milliseconden en zijn ook niet hetzelfde als PostgreSQL-bufferhits.

## 3. Python en eigen instellingen

Installeer Python 3.12; de geteste versie is 3.12.15. Maak in de projectmap een afzonderlijke omgeving:

```powershell
python -m venv .venv-film
.\.venv-film\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Als activatiescripts zijn geblokkeerd, gebruik dan rechtstreeks `.\.venv-film\Scripts\python.exe` voor de Python-opdrachten. Een algemene wijziging van beveiligingsinstellingen is niet nodig.

Open de nieuwe `.env` lokaal en vervang alle placeholders door eigen gegevens:

| Instelling | Waarde |
| --- | --- |
| `PG_DSN` | Login `film_demo_owner`, eigen wachtwoord, juiste poort, database `film_demo` |
| `NEO4J_URI` | Bolt-adres van de gestarte lokale instance |
| `NEO4J_DATABASE` | Exact `film-demo` |
| `NEO4J_USERNAME`, `NEO4J_PASSWORD` | Eigen beheeraccount voor laden, indexen en het aanmaken van het leesaccount |
| `NEO4J_READER_USERNAME` | Exact `film_demo_reader` |
| `NEO4J_READER_PASSWORD` | Apart, zelfgekozen readerwachtwoord |
| `OLLAMA_HOST` | Gewoonlijk `http://127.0.0.1:11434` |
| `EMBEDDING_MODEL` | `embeddinggemma:latest` |
| `LLM_MODEL` | `gemma4:26b` |

Gebruik URL-percentcodering voor speciale tekens in het PostgreSQL-wachtwoord in de DSN. Commit `.env` nooit en deel geen outputs met verbindingsgegevens. Bewaar je wachtwoorden lokaal; zet ze niet in notebookcellen.

## 4. Ollama en modellen

Installeer [Ollama voor Windows](https://ollama.com/download/windows) en start de lokale service. De geteste versie is 0.40.11. Download de modellen eenmaal:

```powershell
ollama pull embeddinggemma:latest
ollama pull gemma4:26b
ollama list
```

De officiële modelpagina's beschrijven [EmbeddingGemma](https://ollama.com/library/embeddinggemma) en [Gemma 4](https://ollama.com/library/gemma4). `gemma4:26b` is groot en vraagt veel geheugen en schijfruimte. Op CPU kunnen modelaanroepen enkele minuten duren. Deze lokale uitvoering gebruikt geen betaalde API, maar wel eigen hardware. Voor alleen bekijken is de installatie niet nodig.

De demo embedt de **ongewijzigde `Movie.samenvatting`** en vragen met hetzelfde model, zonder zelf toegevoegde document- of vraagprefix. Dit is een zichtbare demonstratiekeuze, geen claim van optimale instellingen voor elke toepassing. De geteste vectors hebben 768 dimensies. De code controleert dimensie, modelnaam en modeldigest. Verander je model, genereer dan embeddings opnieuw en controleer de compatibiliteit van de bestaande index.

## 5. Genereren, leesaccount, laden en indexen

Beide demodatabases moeten bestaan. Voer de opdrachten in deze volgorde uit, ook als je de GUI-import al hebt gedaan:

```powershell
python film_demo.py bestanden
python film_demo.py leesaccount
python film_demo.py laden
python film_demo.py embeddings
python film_demo.py controleren
```

`bestanden` genereert importscripts en fictieve bronfiches uit [data/films.json](data/films.json). Wijzig de centrale JSON en genereer opnieuw; onderhoud afgeleide importbestanden en bronnen niet afzonderlijk.

`leesaccount` maakt met het beheeraccount de Enterprise-rol en gebruiker `film_demo_reader`. Het wachtwoord wordt vanuit `.env` als queryparameter meegegeven, zodat je het niet in een queryvenster met geschiedenis hoeft te typen. Een bestaande reader moet hetzelfde wachtwoord hebben als in `.env`: deze opdracht reset het niet. Een gelijknamige bestaande gebruiker met andere rollen veroorzaakt een stop.

Maak de reader **vóór `laden`**: de afsluitende inhoudscontrole gebruikt die reader al. Alle retrieval gebruikt het aparte leesaccount, met leesrechten op `film-demo` en een expliciet schrijfverbod. Import, indexbouw en accountbeheer gebruiken het beheeraccount.

`laden` gebruikt `ON CONFLICT DO NOTHING` en `MERGE`, zodat identieke demo-invoer opnieuw aangeboden kan worden. Het maakt afwijkende bestaande data niet stilzwijgend gelijk. De controle vergelijkt de personen, films, verwachte bronproperties en ACTED_IN-relaties met de JSON en controleert het totale aantal Neo4j-nodes. Afgeleide embeddingproperties tellen niet mee als bronfeiten. Bij drift: **stop**, controleer de databasenamen en onderzoek het verschil.

`embeddings` schrijft samenvattingsvectoren naar de films, maakt `film_vector` en `movie_text` aan en wacht op indexopbouw. De vectorindex zoekt in `Movie.embedding`, afgeleid van uitsluitend `Movie.samenvatting`. De fulltextindex doorzoekt `title` en `samenvatting`. Controleer in Neo4j:

```cypher
SHOW INDEXES YIELD name, type, state, labelsOrTypes, properties
RETURN name, type, state, labelsOrTypes, properties;
```

De twee zoekindexen moeten `ONLINE` zijn. `ACTED_IN`-relaties zitten buiten deze indexen en worden afzonderlijk met Cypher gevolgd. Het notebook controleert embeddingcompatibiliteit opnieuw vóór retrieval.

Voor een werkelijk lege herbouw: controleer in de GUI eerst exact **`film_demo`** respectievelijk **`film-demo`**. Verwijder uitsluitend de bedoelde demodatabase via de GUI, maak haar opnieuw aan en volg de importstappen opnieuw. Gebruik geen onbeperkte verwijderquery op een instance met andere data.

## 6. Notebook uitvoeren en exporteren

Registreer vanuit de geactiveerde demoomgeving de kernel:

```powershell
python -m ipykernel install --user --name film-demo --display-name 'Python 3 (filmdemo)'
```

Open [demo.ipynb](demo.ipynb) in je notebookeditor en kies **Python 3 (filmdemo)**. Of voer alles vanuit de terminal uit:

```powershell
python -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=3600 demo.ipynb
python -m nbconvert --to html --embed-images --HTMLExporter.theme=dark demo.ipynb
```

De eerste opdracht slaat werkelijke outputs in het notebook op; de tweede maakt `demo.html` met ingesloten afbeeldingen. Houd databases en Ollama actief. De tijdslimiet geldt per cel; lokale modeluitvoering kan lang duren.

De vijf officiële retrievers staan in [retrieval.py](retrieval.py). De vaste relatieverrijking staat in [queries/verrijking.cypher](queries/verrijking.cypher). [notebook_view.py](notebook_view.py) presenteert rijen, uitgevoerde queryketens, parameters, exacte context en antwoorden. Nieuwe modelantwoorden kunnen verschillen. Controleer bronnen en context naast de formulering. Raadpleeg [BRONNEN.md](BRONNEN.md) voor pakketdocumentatie en filterbeperkingen.

## 7. Een les geven

Open vooraf de opgeslagen notebookuitvoer of HTML. Zet pgAdmin op `film_demo` en de Neo4j-queryomgeving op `film-demo` klaar. Begin met de graaf en vraag A, voer de centrale collegaqueries uit en bekijk Explain Analyze en PROFILE. Vergelijk daarna de opgeslagen RAG-contexten: welke tekst ondersteunt een inhoudelijke kandidaat, en welke relatie ondersteunt samenwerking? Plan extra tijd voor opnieuw gegenereerde CPU-antwoorden.

## Problemen oplossen

| Probleem | Controle en vervolg |
| --- | --- |
| PostgreSQL onbereikbaar | Draait de service? Kloppen host en poort in pgAdmin en `PG_DSN`? Getest: 5433; standaard kan 5432 zijn. |
| Verkeerde database | PostgreSQL moet `film_demo` zijn; Neo4j `film-demo`. Gebruik niet de standaarddatabase `neo4j`. |
| Aanmelden mislukt | Controleer eigen accounts, DSN-percentcodering en het aparte readerwachtwoord lokaal. Toon ze niet in outputs. |
| Driver- of importfout | Gebruik Python 3.12, de demoomgeving en `requirements.txt`. Controleer de geselecteerde kernel. |
| Neo4j onbereikbaar | Start instance en database; controleer Bolt-adres en poort. Deze route met meerdere databases en rollen vereist Enterprise. |
| Ollama offline of model ontbreekt | Start Ollama, controleer `OLLAMA_HOST` en `ollama list`; download exact de modelnamen uit `.env`. Na downloaden kan de lokale uitvoering zonder internet. |
| Index ontbreekt of niet online | Voer `python film_demo.py embeddings` uit en controleer `SHOW INDEXES`. Wacht op `ONLINE`; lees een eventuele schema- of dimensiefout. |
| Embeddingmodel of dimensie wijkt af | Controleer naam en digest; genereer opnieuw. Bij een incompatibele index stopt de code. Herbouw zo nodig uitsluitend de gecontroleerde demodatabase volgens stap 5. |
| Inhoudscontrole mislukt | Ga niet door met afwijkende feiten. Controleer databasekeuze en JSON; herbouw desgewenst uitsluitend de lege demodatabases. |
| Model duurt lang | CPU-uitvoering kan minuten vragen. Bekijk de opgeslagen uitvoering of wacht; start geen reeks dubbele uitvoeringen. |

De geteste versies staan in [README.md](README.md). Bronfiches S1–S4 zijn fictief en uitsluitend bedoeld voor onderwijs.

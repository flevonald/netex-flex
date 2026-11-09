# Genereer NeTEx XML vanuit CSV

Deze map bevat een script dat een NeTEx-flex XML bestand maakt for Flevoland.
FlexRRReis Flevoland is een vorm van oppervlakte-flex in en rond Flevoland. Vanuit alle plekken mag naar alle andere plekken gereisd worden.
Alle vervoersvoorwaarden: [https://flexrrreisflevoland.rrreis.nl/vervoersregelement](https://flexrrreisflevoland.rrreis.nl/vervoersregelement)

De netex-standaard kan gevonden worden op: [https://bison.dova.nu/standaarden/nl-netex-nederlands-netex-profiel](https://bison.dova.nu/standaarden/nl-netex-nederlands-netex-profiel)

## Files
- `create_stops.py`: Python generator of stops.csv.
- `generate_netex_from_csv.py`: Python generator.

- `export_config_template.csv`: CSV template with export metadata, operator, line and booking details.


## Create Stops
Met flexRRReis Flevoland kun je reizen tussen alle adressen in de gemeentes Dronten, Lelystad, Noordoostpolder, Urk en Zeewolde. Daarnaast kan naar hubs rondom de provincie gereisd worden.
In deze netex-flex worden alle adressen in het reisgebied opgenomen als punt in dat gebied. Daarnaast worden de hubs toegevoegd.

### Adressen
Worden bepaald door de grenzen van de gemeenten te pakken en binnen deze grenzen de 
`Bestuurlijke grenzen`
`Bag-light`

### Hubs
`hubs.csv`
`chb stopplaces`
De hubs die gebruikt mogen worden staan in een lijst. Uit het CHB wordt hun locatie en officiële naam toegevoegd.

### Issues
* Slechts 500 adressen in Lelystad en Dronten voor test.
* Bushaltes in het gebied zijn nog niet toegevoegd.
* Methode maakt een vierkant rond het gebied en selecteert vervolgens op plaatsnaam. Voor overige plaatsen binnen gemeente gaat dit dus nog niet goed.
* Naam en korte naam zijn nu combinatie `straat, huisnummer, plaats`

### flexible_stop_places_template.csv

- `stop_code`: Code used in XML IDs (example: `almkerk`).
- `name`: Public name (example: `Almkerk`).
- `short_name`: ShortName field.
- `x`: x-coordinate (EPSG:4326).
- `y`: y-coordinate (EPSG:4326).

## Genereer Netex
Op dit moment is er één gebied en 17 hubs.
Zowel de gebieden als de hubs worden als FlexibleStopPlace genoemd. 
Voor de gebieden worden daar alle adressen als member toegevoegd. De hubs hebben maar 1 member.
Zowel de adressen als de hubs zijn een ScheduledStopPoint.

Er zijn timinglinks en service journeys voor:
* de gebieden met zichzelf
* de gebieden met elkaar v.v.
* de gebieden met de hubs v.v. 

### Issues
* No indication of assistance (wheelchair, scootmobiel, guide-dog)
* Reizen binnen Flevoland naar haltes nog niet benoemd, deze haltes moeten net als de adressen aan gebied Flevoland toegevoegd worden. 
* OV-toets: ![OV-toets](https://lirp.cdn-website.com/4b1a9462/dms3rep/multi/opt/ov+toets-124c6214-1920w.png)
* Soort ritaanvraag: Ride at desired departure / Public Transport Connection.
* `runtimes` niet opgegeven
* Omrijtijd nog niet goed gedefinieerd. Alleen `safe_duration_factor` en `safe_duration_offset` opgenomen.
* Tarief
* Feestdagen nog niet apart benoemd in availabilityconditions. Uitgegaan wordt van standaard week over hele jaar.

* Flevoland heeft nog geen officiële codespace.
* Nog geen voertuiginformatie toegevoegd.

## export_config_template.csv
One row only. Main fields include:
- Publication and frame metadata: `publication_timestamp`, `participant_ref`, `description`, `codespace`, `version`, `frame_key`, `valid_from`, `valid_to`
- Organisation and service metadata: `organisation_name`, `operator_code`, `operator_name`, `operator_url`, `zone_name`, `zone_short_name`, `zone_description`, `line_code`, `line_name`, `safe_duration_factor`, `safe_duration_offset`
- Booking metadata: `booking_phone`, `booking_url`, `booking_further_details`, `booking_methods`, `booking_access`, `book_when`, `latest_booking_time`, `minimum_booking_period`, `booking_note`

## Run
Run python files.

```
```

## Validate NeTEx XML

Install the XSD validator once:

```powershell
python -m pip install lxml
```

Validate an XML file:

```powershell
python validate_netex.py NeTEx_PFL_FlexRRReisFlevoland_20261023.xml
```

By default, the script downloads the current BISON schemas from the `master` branch on each run. It uses `netex-nl-geen-constraints.xsd`, the official entry point that includes `netex-nl.xsd` and declares `PublicationDelivery`. This checks XSD structure and types, but not the additional identity constraints or Schematron rules.

For offline validation or a specific schema release, download the BISON XSD directory and specify its entry-point schema. Keep all referenced XSD files alongside it:

```powershell
python validate_netex.py my-export.xml --schema path/to/xsd/netex-nl-geen-constraints.xsd
```

To also check the XSD identity constraints, use `netex-nl-met-constraints.xsd` as the entry point instead. The exit code is `0` for valid XML, `1` for invalid XML and `2` when validation could not be completed.

## Notes
- The script validates required columns and required values.
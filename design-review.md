# Frontend Design Review — Corvin

Stand: 2026-11-03. Grundlage: Klick-Durchgang durch alle Views (1440×900, Dark Mode, 375 px Mobile) mit Testdaten in einer separaten Scratch-DB, plus Code-Audit aller `.vue`-Dateien. Pfade relativ zu `frontend/src/`.

Legende: 🔴 Bug / blockiert Workflow · 🟠 deutlich spürbar · 🟡 Feinschliff

---

## 1. Echte Bugs (zuerst fixen)

Status 2026-11-03: Alle Punkte dieser Tabelle sind behoben. Die letzten drei Zeilen kamen beim Testen der Fixes dazu.

| | Wo | Problem |
|---|---|---|
| ✅ | `views/TasksView.vue:79` `toggleDone` | Erledigt-Haken schickt `PUT` mit nur `{status}` → **400**. Fehler wird verschluckt, Checkbox bleibt optisch angehakt, Status bleibt „Offen“. `PATCH` verwenden + `notify.error`. |
| ✅ | `components/ui/AppDataTable.vue:281` | Mobile-Kartenansicht fällt auf `row.id` zurück. Rechnungspositionen in der Rechnungsdetailansicht zeigen auf dem Handy **nur UUIDs**. Gleiches gilt für jede Tabelle ohne `#card`-Slot/`mobileCard` (Zahlungen, Wizard-Einträge, Vertragszeiten …). → Generischer Fallback rendert jetzt die Spalten als Label/Wert. |
| ✅ | `composables/useConfirmDelete.ts` | `accept: action` ohne `catch` und ohne Erfolgs-Toast → jedes vom Backend abgelehnte Löschen (z. B. `PROTECT` bei Kunde mit Rechnungen) scheitert lautlos. |
| ✅ | `components/ui/AppDurationDisplay.vue:9` | `Math.round(minutes % 60)` → bei Bruchteilen erscheint `0:60 h`. Erst auf ganze Minuten runden, dann teilen. |
| ✅ | `views/invoices/InvoiceDetailView.vue:62` | `emailForm.to = … ? '' : ''` — toter Code, E-Mail-Empfänger wird nie aus den Rechnungskontakten vorbefüllt. |
| ✅ | `views/invoices/InvoiceListView.vue:83,99` / `InvoiceDetailView.vue:129` | „(teilw.)“ hart codiert, unterschiedliche Keys, Mobile-Karte ignoriert `partially_paid`. |
| ✅ | `components/ui/AppModal.vue:38,51` | `closed` feuert doppelt (`close()` + `@hide`). |
| ✅ | Inaktive Kunden/Verträge (`CustomerListView:109`, `ContractListView:107`) | Werden als **roter** Tag mit Label „—“ angezeigt (Status `cancelled`). Sieht wie ein Fehler aus. |
| ✅ | `composables/useNotify.ts` | Backend-Fehler als Liste (z. B. `["Kein Bankkonto mit IBAN…"]`) erschienen als „0: …“ im Toast. |
| ✅ | `InvoiceDetailView.vue` E-Mail-Dialog | Der Bestätigen-Button hieß „Speichern“ statt „Senden“. |
| ✅ | Backend `OwnedViewSet.perform_destroy` | Löschen eines Kunden mit Rechnungen/Zeiteinträgen (`on_delete=PROTECT`) lieferte **500**. Das Backend antwortet jetzt mit 400 und einer übersetzten Meldung (pro Ressource über `protected_message` anpassbar). |

## 2. Workflows, die unintuitiv sind

### Rechnung erstellen (wichtigster Flow)
- ✅ ~~**Entwurf ist nach dem Erstellen nicht editierbar** — weder Positionen, Datum, Fälligkeit, MwSt. noch Notizen. Nur das Bankkonto. Ein Tippfehler heißt: Entwurf löschen, neu anlegen. Gerade der Entwurfsstatus sollte voll bearbeitbar sein.~~ → Kopfdaten (Datum, Fälligkeit, MwSt., E-Rechnung, Kontakte, Notizen) per „Bearbeiten“; Positionen per Zeilenklick bearbeiten, hinzufügen, löschen (`/api/v1/invoice-items/`). Summen werden neu berechnet, die Vorschau lädt neu. Gelöschte Positionen geben ihre Zeiteinträge wieder frei (`TimeEntry.invoice_item`).
- ✅ ~~Wizard-Schritt 2 listet die Zeiteinträge, **man kann aber keine abwählen**. Es fehlen Betrag/Stundensatz pro Zeile und eine Summe — man sieht erst nach „Erstellen“, was die Rechnung kostet.~~ → Checkboxen pro Eintrag (+ alle), Zwischensumme live über `consolidate_preview`; ein fehlender Stundensatz erscheint als Warnung statt erst beim Erstellen.
- ✅ ~~Schritt 3 hat keine Zusammenfassung (Netto/Brutto, Anzahl Rechnungen bei Gruppierung), kein Rechnungs-/Fälligkeitsdatum.~~ → Zusammenfassung mit allen Positionen, Netto, MwSt., Brutto; Daten sind am Entwurf editierbar.
- ✅ ~~„Weiter“ heißt „Bestätigen“, Schritt 3 heißt „Rechnungen“, Schritte sind per Klick überspringbar (`:readonly="false"`) → Schritt 3 ohne Kunde erreichbar. Kein Abbrechen-Button.~~ → „Weiter“, „Prüfen & erstellen“, Abbrechen, Schritte ohne Kunde gesperrt.
- ✅ ~~Im Schritt 2 ist „Position hinzufügen“ genauso primär wie „Bestätigen“ — zwei konkurrierende Primary-Buttons. Eine leere manuelle Zeile ist immer vorbelegt.~~ → Text-Button, deaktiviert ohne Beschreibung.
- 🟡 Positionstexte doppeln Infos: „03.11.2026 — Website-Relaunch: Arbeit #0 an Website-Relaunch“.
- ✅ ~~Die Positionstabelle links scrollt horizontal; Menge/Preis/Summe sind abgeschnitten, obwohl rechts die Vorschau Platz verschenkt.~~
- 🟡 Generierte Positionstexte sind teils hart auf Englisch im Backend: „consulting services“ (Gruppierung pro Projekt) und „Services“ bei fehlender Beschreibung (`services/consolidation.py`). Dokumente sollen in `LANGUAGE_CODE` erscheinen.
- ✅ Positionen werden jetzt chronologisch erzeugt (vorher in der Reihenfolge der Eintrags-IDs).
- ✅ ~~Finalisieren scheitert erst im letzten Moment mit „kein Bankkonto mit IBAN hinterlegt“. Diese Voraussetzung sollte schon im Wizard (Schritt 3, Bankkonto) bzw. als Hinweis am Entwurf sichtbar sein, mit Link zu Einstellungen → Bankkonten.~~ → Hinweis am Entwurf und im Wizard-Schritt 3 mit Link zu Einstellungen → Bankkonten (`/settings?tab=bankAccounts`).
- ✅ ~~Im Bestätigungsdialog (Finalisieren) sind „Abbrechen“ und „Finalisieren“ beide gefüllte Primary-Buttons~~ → „Abbrechen“ ist in allen Bestätigungsdialogen ein Text-Button.
- 🟡 Im E-Mail-Dialog sind Betreff und Text leer, obwohl bei leeren Feldern die Vorlage greift. Besser mit der Vorlage vorbelegen oder als Platzhalter anzeigen.
- 🟡 Vorschau zeigt „EUR“, die App „€“; der „Entwurf“-Status-Tag steht zwischen den Buttons und sieht selbst wie ein Button aus.

### Zeiterfassung
- ✅ ~~„Timer starten“ legt sofort einen Eintrag **ohne Kunde/Projekt/Beschreibung** an. Stoppt man auf der Seite, kommt keine Nachfrage.~~ → Start-Dialog (Beschreibung, Kunde, Projekt; Projekt füllt den Kunden), überall gleich (Seite und Header-Widget). Stoppen auf der Seite löst denselben Folgedialog aus wie im Widget; beides läuft über den Timer-Store und das Widget.
- ✅ ~~Ohne Filter (Kunde/Projekt/Zeitraum/abgerechnet)~~ → Filter mit Summe („27 Einträge · 31:15 h“) über `/time-tracking/summary/`.
- ✅ ~~Offen: Gruppierung nach Tag mit Tagessummen.~~ → Gruppiert nach Tag mit Tagessumme (bei Sortierung nach Datum; Summen beziehen sich auf die geladene Seite).
- ✅ ~~Zwei Timer-Anzeigen gleichzeitig, Pause nur im Header~~ → Seite zeigt Pause/Fortsetzen + Stoppen, die Uhr nur noch im Header.
- ✅ ~~Start und Ende wiederholen jeweils das volle Datum~~ → Datum | 19:59–20:44.
- ✅ ~~Bereits abgerechnete Einträge haben einen Löschen-Button.~~ → ausgeblendet; das Backend lehnt das Löschen abgerechneter Einträge ab.
- ✅ Kunde/Projekt-Auswahlen lassen sich leeren und haben Platzhalter; ein Projekt fremder Kunden wird beim Kundenwechsel verworfen.
- 🟡 Backend-Meldungen der Timer-Endpunkte („A timer is already running.“ …) sind nicht übersetzt.

### Filter (alle Listen)
- ✅ Einheitliche `AppFilterBar` in der Tabellen-Toolbar (`AppDataTable` `#toolbar`, gleiche Zeile wie „Auswählen“): ein „Filter“-Button mit Zähler öffnet die Felder im Popover, aktive Filter erscheinen als entfernbare Chips, rechts optional eine Zusammenfassung. Eingesetzt in Zeiterfassung (Kunde, Projekt, Zeitraum, Status), Rechnungen (Kunde, Status) und Aufgaben (Kunde, Status, Priorität); die Status-Selects im Seitenkopf sind entfallen.
- 🟡 Kunden, Projekte, Verträge und Termine haben noch keine Filter (Kunden nur die Suche im Seitenkopf); bei Bedarf dieselbe Leiste verwenden.
- 🟡 Status-/Prioritäts-Selects ohne `option-label` haben als Accessible Name den Rohwert („open“, „in_progress“) statt des übersetzten Textes.

### Aufgaben
- ✅ ~~Die erste Checkbox-Spalte (Erledigt) ist nicht von einer Auswahl-Checkbox zu unterscheiden; dazu gibt es noch „Auswählen“. Die `#`-Spalte ist leer.~~ → runder Erledigt-Schalter mit Tooltip, erledigte Aufgaben durchgestrichen. Die leere „#“-Spalte kam nur von Testdaten ohne Nummer.
- 🟡 Erledigte Aufgaben werden in der Tabelle nicht durchgestrichen bzw. ausgegraut (nur auf der Mobile-Karte).

### Kunden und Projekte
- ✅ ~~Die Kundendetailseite ist ein reines Bearbeitungsformular: **keine Projekte, Rechnungen, offenen Beträge, Zeiten** des Kunden. Man springt ständig zwischen Listen. Ein „Übersicht“-Tab mit Kennzahlen und verknüpften Listen wäre der größte Hebel. Für Projekte gilt dasselbe: keine Zeiteinträge, Aufgaben, Rechnungen.~~ → Neuer erster Tab „Übersicht“ bei Kunde und Projekt (`RelatedOverview`): Kennzahlen (nicht abgerechnet, offene Rechnungen, offene Aufgaben, aktive Projekte bzw. erfasste Stunden) und Listen für Projekte, letzte Zeiteinträge, Rechnungen und offene Aufgaben. „Alle anzeigen“ öffnet die jeweilige Liste gefiltert (`?customer=`/`?project=`), „Rechnung erstellen“ öffnet den Wizard vorbelegt.
- ✅ ~~Der Speichern-Button bleibt auf allen Tabs sichtbar, obwohl Ansprechpartner/Adressen/Stundensätze sofort per Modal speichern. Man weiß nicht, was er speichert. Gleiches gilt für Einstellungen (Bankkonten, Bilder) und Vorlagen. Außerdem ist der Seitenkopf nicht sticky, sodass Speichern bei langen Formularen aus dem Bild scrollt.~~ → Speichern nur noch auf Tabs mit Formular (Kunde/Projekt/Vertrag: „Stammdaten“; Einstellungen: Unternehmen, Nummerngenerierung, Zeiterfassung; Vorlagen: Zuordnung).
- 🟡 Leerer Tab „Stundensätze“ verschweigt, dass der Standardsatz (95 €) greift. Ein Hinweis „Es gilt der Standardsatz …“ fehlt.
- ✅ ~~Die Projektdetailseite hat eine Tab-Leiste mit genau einem Tab („Anhänge“)~~ → Übersicht / Stammdaten / Anhänge; der Kunden-Tab „Profil“ heißt jetzt „Stammdaten“. Der Vertrag hat weiterhin keine Tabs.

### Verträge
- ✅ ~~Verträge sind nach dem Anlegen **nicht editierbar**~~ → Tabs „Übersicht“ / „Stammdaten“ wie bei Kunde und Projekt. Das Formular (`ContractFormFields`) teilen sich Anlegen und Bearbeiten, mit korrekten Labels („Vertragsbeginn“, „Vertragsende“, „Aktiv“) und Pflichtmarkierungen. Das Anlegen-Formular wird beim Öffnen zurückgesetzt und meldet Erfolg.
- ✅ ~~„Jetzt abrechnen“ erzeugt ohne Rückfrage eine Rechnung.~~ → mit Bestätigung.
- ✅ Inklusivstunden als „8:00 h“ statt „8h“.

### Vorlagen
- ✅ ~~Unter „Zuordnung“ stehen Gutschrift, Angebot, Bestellung, Lieferschein — Belegarten, die es in der App nicht gibt. Gleichzeitig zeigt „Rechnung“ „Keine Vorlage“, obwohl „Standard (DIN A4)“ existiert und benutzt wird. Es bleibt unklar, was eigentlich gilt.~~ → Belegarten bleiben (kommen später); ohne Zuordnung steht jetzt „Standard: <Vorlage>“.
- ✅ ~~„Neu“ legt sofort eine Vorlage auf dem Server an; wer zurückgeht, behält einen Datenmüll-Eintrag.~~ → Dialog „Neue Vorlage“ mit Name, angelegt erst beim Bestätigen.
- 🟡 Designer: Die Vorschau ist nicht auf die Breite skaliert (A4 wird rechts abgeschnitten, horizontaler Scroll), die Tabs laufen über („Fußzeilen-HT…“ + Pfeil), Scrollbereiche sind verschachtelt, und die Vorschau aktualisiert erst nach Speichern. Untertitel „Rechnungsdesigner“, obwohl Vorlagen für mehrere Belegarten gedacht sind.

### Allgemein
- ✅ ~~**Kein Unsaved-Changes-Schutz** (Formulare, Designer-Editoren, Wizard); auch Esc/X im Modal verwirft Eingaben.~~ → `useUnsavedChanges` fragt vor Routenwechsel/Tab-Schließen (Kunde, Projekt, Vertrag, Termin, Einstellungen, Designer, Wizard); `AppModal` mit `form` fragt bei X/Esc/Abbrechen. Offen: das Zeiteintrag-Modal (eigenes Formular in `TimeEntryForm`).
- ✅ ~~Keine Zurück-Navigation/Breadcrumbs auf Detailseiten.~~ → Zurück-Link im `AppPageHeader` (`back-to`) auf allen Detailseiten, Sicherheit und Wizard.
- ✅ ~~Detailseiten, die nicht laden (404/Fehler), bleiben **leer** — kein Spinner, keine Meldung.~~ → `AppLoadState` zeigt Spinner bzw. Meldung mit Link zur Liste.
- ✅ ~~„Auswählen“ auf jeder Liste führt ins Leere: Es gibt keine Bulk-Aktionen. Bis welche existieren, den Button entfernen.~~ → Sammel-Löschen „Löschen (n)“ mit Rückfrage; Abgelehntes wird gezählt gemeldet. „Auswahl löschen“ heißt jetzt „Auswahl aufheben“.
- ✅ ~~Zeilenaktionen (Löschen/Bearbeiten) werden erst beim Hover sichtbar (`style.css:54`), die Spalte „Aktionen“ wirkt leer. Zusätzlich zeigt `cursor-pointer` auf allen Tabellen, auch auf read-only (Rechnungspositionen, Zahlungen).~~ → mit dem Tabellen-Redesign behoben (gedimmt sichtbar, `cursor-pointer` nur bei klickbaren Zeilen).
- ✅ ~~Fehlendes Feedback: Erfolgs-Toasts fehlen bei Vertrag/Termin anlegen, Aufgaben, Zeiteinträgen, Kunden-Unterobjekten und Einstellungen-Modalen. Ohne `try/catch` laufen TimerWidget, Anhänge, Sitzungen widerrufen und Dashboard-Load. Ohne `:loading` sind viele Modale doppelt absendbar.~~ → Erfolgsmeldungen und Fehlerbehandlung ergänzt (Termin, Aufgaben, Zeiteinträge, Kunden-Unterobjekte, Einstellungen-Modale, Textbausteine, Anhänge inkl. Lösch-Rückfrage und „Hochladen“, Sitzungen abmelden mit Rückfrage, 2FA-Start, Dashboard, Vorlagen).
- 🟡 Die Dashboard-KPIs (offene/überfällige Rechnungen) sind nicht klickbar. Der Umsatzchart ohne Daten zeigt eine leere 0–1,0-Achse statt eines Empty-States.
- 🟡 Sicherheit (Passwort, 2FA) ist nur über einen Textlink im Einstellungen-Header erreichbar.

## 3. Visuelle Inkonsistenzen / „unschön“

- ✅ ~~**Markenfarbe vs. UI-Farbe:** Das Logo hat einen Cyan→Violett-Verlauf, die UI ist flaches Mittelblau, die Charts nutzen Chart.js-Standardfarben (blau/grün/orange). Drei Farbwelten. Vorschlag: Primary aus dem Logo ableiten (Violett-Blau), Chart-Palette aus Primary/Surface-Tokens.~~ → Diagramme nutzen eine Palette aus den drei Logo-Farben (`theme/brand.ts`); aktiver Menüpunkt mit `bg-primary/10` statt `bg-blue-50`. Primary bleibt das Blau aus dem Logo.
- ✅ ~~Bei 1440 px scrollen Kunden-, Vertrags-, Zeiterfassungs- und Rechnungspositionstabellen horizontal (lange Namen brechen nicht um, viele Spalten). Lange Texte mit `truncate` + Tooltip versehen, unwichtige Spalten ausblenden.~~ → mit dem Tabellen-Redesign behoben (`app-text`-Spalten mit „…“ und Tooltip).
- ✅ ~~Der Sprachwähler im Topbar ist abgeschnitten („Deut…“). Er gehört eher in Einstellungen/Benutzermenü; „Abmelden“ als blauer Primary-Link ist zu prominent.~~ → kompakt „🌐 DE“, Abmelden als dezenter Text-Button.
- ✅ ~~Das Hamburger-Menü erscheint auch auf Desktop, obwohl die Sidebar sichtbar ist.~~ → nur noch unterhalb `lg`.
- 🟡 Die Login-Seite ist sehr karg: nur Platzhalter statt Labels, eigene Fehlerdarstellung, kein Hintergrund/Branding.
- 🟡 Rote Töne gibt es doppelt (`text-red-500` vs. `--p-red-500`). Das aktive Nav-Item nutzt `bg-blue-50` statt Primary-Token, die Vorschau `bg-neutral-200`, und `text-green-600` hat im Dark Mode schlechten Kontrast. Dazu kommen hart codierte Hex-Farben im Dashboard.
- 🟡 Karten: Dashboard/Rechnung mit Hintergrund, Vertrag/Projekt/Sicherheit ohne. Überschriften mal `h2 font-semibold`, mal `h3 font-medium`, mal `fieldset legend`. Tab-Panels mal mit, mal ohne `pt-4`. Formularbreiten `max-w-lg`/`2xl`/`3xl`/`4xl` gemischt.
- 🟡 Formate: ~~Dauer `5h` (Verträge)~~ (behoben) vs. `5:00 h` vs. `HH:MM` (TimeEntryForm). Budget „40“ ohne Einheit neben „10:15 h“ — besser als Fortschrittsbalken. Auf dem Dashboard steht „(0)“ winzig hinter Beträgen.
- 🟡 „Mittel“ (Priorität) und „Offen“ (Status) haben dieselbe blaue Tag-Farbe.
- 🟡 Die Nummer erscheint auf Detailseiten als (scheinbar editierbares) Input statt im Header-Untertitel. Visit-Titel zeigen ein ISO-Datum.
- 🟡 Es gibt drei verschiedene Upload-Patterns, und der Anhang-Upload ist mit „Erstellen“ beschriftet.
- 🟡 Modale: Buttons stehen mal im Footer, mal im Body, mal zentriert. Grid-Layouts in Modalen (`grid-cols-3/5`) werden auf dem Handy zu eng.
- 🟡 Seitenwechsel zeigen kurz eine komplett weiße Seite (Lazy-Route ohne Skeleton).

## 3a. Tabellen-Redesign (Wunsch: alle Tabellen überarbeiten)

**Status 2026-11-03: umgesetzt.**
- **Header:** `0.8125rem`, gedämpft, `font-weight 500`, eigener Hintergrund (`surface-50` hell, `surface-950` dunkel). Sortier-Icon erscheint nur bei Hover und in der sortierten Spalte; die blaue Fläche der sortierten Spalte ist weg.
- **Zeilen:** 38 px statt 49 px; `text-sm`, `tabular-nums`, kleinere Tags; die Icon-Buttons treiben die Zeilenhöhe nicht mehr.
- **Zahlenspalten:** Beträge, Dauern und Mengen sind über `<Column class="app-num">` rechtsbündig.
- **Textspalten:** Name, Beschreibung, Kunde, Projekt usw. sind über `<Column class="app-text">` einzeilig mit „…“ und teilen sich den Restplatz, mit Tooltip bei abgeschnittenem Text. Es gibt kein horizontales Scrollen mehr.
- **Zeilenaktionen:** Sie sind gedimmt (35 %) statt unsichtbar.
- **Klickbarkeit:** `cursor-pointer` erscheint nur bei Tabellen mit `@row-click`.
- **Mobile-Karten:** Sie sind kompakter.
- **Gespeicherte Spaltenbreiten:** Die Tabellen-State-Keys wurden versioniert angehoben, weil alte Spaltenbreiten aus `localStorage` das neue Layout sonst zusammengedrückt hätten. Dadurch werden Sortierung und Spaltenbreiten einmalig zurückgesetzt.
- **Offen:** Die Toolbar („Auswählen“ in eigener Zeile über der Tabelle) und der Dichte-Umschalter sind nicht umgesetzt.

Ursprünglicher Befund:

🟠 Die Tabellen wirken überdimensioniert und gehören neu gestaltet, aber im bestehenden Stil der App: flach, eckig, Aura-Surface-Töne, Primary als Akzent.

- **Header zu groß/zu laut:**
  - Aura-Default-Padding und fette Schrift in normaler Größe; die Sortier-Icons stehen bei *jeder* Spalte permanent da.
  - Der sortierte Header bekommt einen blauen Hintergrund.
  - Vorschlag:
    - kleinere Schrift (`text-xs`/`0.75rem`), `font-medium`, gedämpfte Farbe (`surface-500`), optional Uppercase mit leichtem Tracking;
    - Padding ca. `0.5rem 0.75rem`;
    - Hintergrund `surface-50` bzw. `surface-900` (dark) mit einer Linie darunter;
    - Sortier-Icon nur beim Hover und in der aktiven Spalte;
    - aktive Spalte nur über Icon und Textfarbe markieren, nicht über eine Fläche.
- **Zeilen zu hoch:**
  - Ca. 52 px pro Zeile → auf 1440×900 passen knapp 12 Einträge.
  - Ziel ca. 36–40 px (Padding `0.5rem 0.75rem`, `text-sm`). Damit passen etwa 50 % mehr Zeilen auf den Bildschirm.
  - Tags (Status/Priorität) in der Zeile kleiner machen (`text-xs`, weniger Padding), damit sie die Zeilenhöhe nicht treiben.
- **Ruhigere Zeilen:**
  - Nur horizontale Trennlinien in `surface-100`/`surface-800`, dezenter Hover-Hintergrund.
  - Kein `cursor-pointer` auf read-only Tabellen.
- **Zahlen & Ausrichtung:**
  - Beträge, Dauern und Mengen rechtsbündig mit `tabular-nums`; Header-Ausrichtung passend zur Spalte.
- **Breite:**
  - Lange Texte mit `truncate` + `title`-Tooltip statt horizontalem Scroll.
  - Spalte „Aktionen“ schmal und ohne Header-Text (oder Icon-Spalte rechts, fixiert).
- **Toolbar:**
  - Suche/Filter, „Auswählen“ und Paginator in eine kompakte Zeile direkt über bzw. unter der Tabelle bringen, statt „Auswählen“ einzeln rechts darüber schweben zu lassen.
- **Umsetzung:**
  - Zentral über `dt`-Tokens im `FlatPreset` (`theme/preset.ts`, Komponente `datatable`: `headerCell.padding`, `bodyCell.padding`, `row.hoverBackground`, `columnTitle.fontWeight`) und `AppDataTable.vue`, nicht pro View.
  - Optional ein `density`-Prop (`compact` als Standard, `comfortable` für Detail-Untertabellen) — passt zum bestehenden Backlog-Punkt „Compact/comfortable density selector“.
  - Auch die Mobile-Kartenliste etwas kompakter machen (weniger Padding, Sekundärinfo in einer Zeile).

## 4. Texte / Terminologie

- ✅ Gleiches Ding, verschiedene Wörter: vereinheitlicht („Verträge“, „Neuer Vor-Ort-Termin“, „Rechnungs-Ansprechpartner“, „Bankkonto“, „Zwei-Faktor-Authentifizierung“, Spalte „Nr.“). Ursprünglich:
  - Nav „Verträge“ vs. Titel „Supportverträge“.
  - „Vor-Ort-Termine“ vs. „Neuer Termin“.
  - „Ansprechpartner“ vs. „Rechnungskontakte“.
  - „Bankkonto“ vs. „Bankverbindung“.
  - „2FA“ vs. „Zwei-Faktor-Authentifizierung“.
  - Spalte „#“ vs. „Nummer“.
- ✅ Falsche Labels: korrigiert (Termin-Spalte „Projekt“, „Vertragsbeginn/-ende“, Zahlungs-„Betrag“, „Aufgabe“, „Stammdaten“, „Ort“ bzw. „Straße und Hausnummer“, 2FA „Deaktivieren“, Backup-Codes „Fertig“, konkrete „Neu“-Labels). Ursprünglich:
  - Visit-Spalte „Projekte“ (Plural).
  - Vertragsbeginn „Datum“, Vertragsende „Ende“.
  - Zahlungsbetrag „Gesamt“.
  - Aufgabentitel „Name“.
  - Kunden-Stammdaten-Tab „Profil“.
  - „Adresse“ ist mal PLZ/Ort, mal Straße.
  - 2FA deaktivieren heißt „Löschen“ und wird mit „Speichern“ bestätigt.
- ✅ Wortwahl: umgesetzt (Website, Kaufmännisch/Abrunden/Aufrunden, ISO-Code, Käuferreferenz (Leitweg-ID), Beginn, „PDF wird erstellt …“). Ursprünglich:
  - „Webseite“ → „Website“.
  - Rundungsrichtung „Nächste/Zurück/Vor“ → „Kaufmännisch/Abrunden/Aufrunden“.
  - „Leitweg-ID“ → „Käuferreferenz (Leitweg-ID)“.
  - „Start“ → „Beginn“.
  - „PDF wird erstellt..“ (zwei Punkte).
- 🟡 Hart codiert: „PLZ“, „Deutschland“, „/h“, „h“-Suffixe, „(teilw.)“, „●“, englische Designer-Labels („contact loop“) sowie die `iframe`-Titel.
- ✅ Du/Sie ist durchgängig „Sie“; de/en-Keys sind vollständig.

## 5. Empfohlene Reihenfolge

1. Bugs aus Abschnitt 1 (kleine, isolierte Fixes).
2. Rechnungsentwurf editierbar machen und Wizard-Schritt 2 mit abwählbaren Einträgen und Beträgen ausstatten.
3. Timer-Flow (Kontext beim Start/Stopp) sowie Filter und Tagesgruppierung in der Zeiterfassung.
4. Globale Muster vereinheitlichen: Fehler-/Erfolgs-Feedback in `useConfirmDelete`/`act`-Helpern, Leave-Guard, Back-Link, sticky Header, „Auswählen“ ausblenden, Hover-Only-Aktionen überdenken.
5. Kunden-/Projekt-Übersichtstab mit verknüpften Daten.
6. Farb-/Token-Aufräumen (Primary aus Logo, Chart-Palette, rote/grüne Tailwind-Klassen raus) und Terminologie-Pass über `de.json`.

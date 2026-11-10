# Odbiór poprawki przeterminowanego szkicu

Zlecenie: https://github.com/artgawlik-ui/ai-focus-3-0/issues/16#issuecomment-6779815037
Baza: PR17 /74e4ceb9f0ba77a0b81861b0482f4069453de4e4.
Ta poprawka nie zmienia produkcji, migracji, flag ani integracji.

## Kryteria odbioru

- Po8 dniach niewysłany szkic o niezmienionym snapshot otrzymuje nowy ID.
- Dotychczasowy szkic, not_sent i reszta historii pozostają niezmienione.
- Dokładnie7 dni pozostaje ważne;7dni+1µs wymaga odnowienia. Prepare i manual_sent
  korzystają ze wspólnej granicy, takiej jak w dotychczasowym potwierdzaniu.
- Świeży szkic jest ponownie zwracany bez tworzenia kopii.
- Równoległe odnowienie tworzy tylko jeden nowy rekord, także po not_sent.
- Faktyczny wcześniejszy kontakt, odmowa, opt-out i zmiana profilu nadal blokują.
- Odnowienie nigdy nie wysyła DM i nie oznacza wysłania lub kontaktu.
- Chromium i WebKit przechodzą od starego niewysłanego szkicu do świeżego przez UI.
- Końcowe push/PR CI muszą potwierdzić ten sam nowy SHA; nie używać poprzednich409 PASS.

## Odtworzenie błędu przed poprawką — RED

Na lokalnym syntetycznym PG17 uruchomiono:

```sh
pytest -q tests/test_sales_draft_expiry.py
```

W pierwszym teście: prepare → not_sent → przesunięcie daty tego syntetycznego Activity
na8 dni wcześniej → manual_sent409 → prepare zwrócił ten sam ID.
Wynik: **1 FAIL**, asercja `Expired unsent draft must not be reused forever`.
Nie wykonywano operacji na prawdziwych rekordach ani edycji historii produkcyjnej.

## Minimalna poprawka

`backend/sales_workflow.py`: wspólne sprawdzenie `current_draft` i użycie go przy
ponownym zwracaniu szkicu oraz potwierdzeniu ręcznej wysyłki. Poprzednio tylko
potwierdzenie sprawdzało wiek. Guardy kontaktu/snapshotu są wykonywane przed
utworzeniem nowego rekordu i pozostają bez zmian. Istniejąca blokada transakcyjna
salonu serializuje oba równoległe prepare. Nie odnawiamy daty starego wpisu.

UI nie wymaga nowego endpointu ani nowego przycisku: dotychczasowy „Przygotuj
indywidualny szkic DM” otrzymuje świeży wpis. Nie ma automatycznego send ani approval.

## Regresja i E2E

Nowych14 przypadków PostgreSQL: odtworzenie8 dni z not_sent, trzy granice czasu,
dwa równoległe warianty z/bez not_sent, cztery kanały wcześniejszego kontaktu,
trzy blokady CRM/Meta/odmowa oraz ponowna weryfikacja zmienionego profilu.

```sh
pytest -q tests/test_sales_draft_expiry.py tests/test_sales_workflow.py
```

Lokalnie: **35 PASS** (14 nowych +21 istniejących), bez skipów. Dwa istniejące
ostrzeżenia deprecacyjne testowych bibliotek nie są błędami.

Rozszerzony `tests/sales_day_browser.py` w obu silnikach:

1. Utworzenie i weryfikacja profilu, przygotowanie szkicu oraz not_sent.
2. Zmiana czasu tylko tego syntetycznego wpisu w lokalnej focus3_ci_*.
3. Odrzucenie starego manual_sent409 i odnowienie przez prawdziwy przycisk UI.
4. Sprawdzenie nowego ID, zachowania starego, braku fałszywego wysłania i dalszej
   ścieżki ręczna deklaracja → odpowiedź → zadanie → wizyta → raport.

W tej wersji kohorta10 salonów ma3 szkice zamiast dawnych2, ponieważ zachowano
przeterminowany. Nadal ma2 deklaracje wysyłki,1 odpowiedź,1 odmowę i0 fikcyjnych
API receipts. Do sales-day.json dodano expired_unsent_draft_renewed/old_draft_preserved.
Starszy SYNTHETIC_RESULTS.json jest datowaną próbką pierwotnego odbioru, nie nowym CI.

Pełne CI niezmienionego workflow obejmuje backend, build, dotychczasowy Chromium/WebKit
z prawdziwym SW/PWA/offline oraz rozszerzony dzień pracy. Profil fault-injection nadal
blokuje SW dla routingu i zewnętrzny HTTP/DNS/socket, bez zmian polityki. Wszystkie
kontakty/wiadomości są syntetyczne; nie wykonuje się rzeczywistych DM.

Dokładny końcowy SHA, wyniki obu workflow i artefakty są w raporcie odbioru Issue16
oraz opisie tego samego Draft PR17. Dokument nie nadaje z góry statusu SUCCESS CI.

## Rozdzielenie statusów

- PASS_LOCAL: powyższa regresja syntetycznego PG17; końcowe CI potwierdzane osobno.
- MOCK: OSM/Meta inbound/odpowiedzi używają fixture, bez realnego kanału.
- OPERATOR: rzeczywista weryfikacja profilu i deklaracje kontaktu nadal wymagają człowieka.
- META_BLOCKED: niezweryfikowany live OAuth/transport, bez aktywacji lub wysyłki.
- PROD_NO_GO: bramki #10–#13 bez zmian; żaden test nie zastępuje produkcyjnego GO.

Następne jedno zadanie: niezależny ponowny odbiór poprawki TTL w Draft PR17.
Bez merge/deploy, zmian Render/DB produkcyjnej/sekretów/sieci, kosztów, nowych usług,
płatnego OpenAI API, Meta/Google lub Focus1.0/2.0.

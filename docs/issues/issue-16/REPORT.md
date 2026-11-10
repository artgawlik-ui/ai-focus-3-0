# Issue 16 — syntetyczny dzień sprzedaży, bez transportu DM

Baza: Draft PR #3, `e37ce5d1ce807b47af18e3354c3232296b8b26c6`.
Gałąź: `feat/issue-16-sales-day`. Nie zawiera zmian rollback z PR #9/#15.
Wznowienie: [zlecenie Fokusa](https://github.com/artgawlik-ui/ai-focus-3-0/issues/16#issuecomment-6777319190).

## Odzyskany stan

Zachowano tę samą lokalną gałąź i pliki. Przed wznowieniem: 5 zmienionych
śledzonych plików i 4 nowe pliki źródłowe/testowe, poza lokalnym symlinkiem
node_modules. Nie wykonano reset/clean, nie otwierano prywatnych archiwów.
395 PASS i poprzednie Chromium/WebKit były wynikami sprzed wznowienia, nie nowym CI.
Ostatnie polecenie poprzedniej sesji nie zapisało guardów; dokończono je teraz.

## Dostarczony przepływ

1. Publiczny OSM mock → źródło i data odczytu → istniejący formularz CRM.
2. Duplikaty odrzuca istniejący unikalny klucz CRM. Ręczne przypisanie do opiekuna
   wykorzystuje istniejące API i RBAC, bez nowej tabeli klientów.
3. W profilu: bezpieczny link wyłącznie do bezpośredniego profilu Instagram;
   ręczne potwierdzenie zgodności profilu, tożsamości i specjalizacji ze źródłem.
   Zmiana danych unieważnia snapshot potwierdzenia i stary szkic.
4. Kwalifikacja wykorzystuje istniejący silnik reguł. Szkic wymienia NAK Hair /
   muk Haircare, faktyczną specjalizację i wizytę 15–20 minut. Nie dodaje produktów,
   cen, pakietów ani proponowanych godzin. Brakujące dane nie są uzupełniane fikcją.
5. `Nie wysłano`, `Wysłano ręcznie`, `Odpowiedział`, `Odmowa` są jawnymi deklaracjami
   operatora z autorem, czasem i źródłem w Activity. Potwierdzenie ręcznej wysyłki
   wymaga skonfigurowanego właściciela, jawnego checkboxa i notatki. Handlowiec nie
   może go zastąpić. Nie powstaje `api_confirmed_sent`, receipt ani sieciowa wysyłka.
6. Istniejący kontakt w dowolnym obsługiwanym kanale blokuje ponowienie pierwszego DM.
   PostgreSQL: advisory lock wspólny z opt-out + blokada salonu, idempotentny klucz
   operacji i odmowa drugiego potwierdzenia również przy dwóch sesjach.
7. Odpowiedź tworzy dokładnie jedno zadanie przeglądu w istniejącym natywnym planerze
   (jeśli planer/schemat są włączone). Inicjatywa klienta w sprawie terminu jest
   zapisywana oddzielnie; propozycja w ramach tego procesu wymaga tego zapisu.
   Istniejące potwierdzanie przez managera, konflikty i zmiany terminu pozostają.
8. Rzeczywiste deklarowane kontakty są uwzględniane przez monitoring i raporty;
   sam szkic, task i plan wizyty nie zmieniają daty kontaktu.
9. Odmowa, również późniejsze wycofanie po pozytywnej odpowiedzi, ustawia zakaz kontaktu. Opt-out Meta również blokuje panel i kolejkę,
   nawet jeśli starszy rekord salonu nadal ma niezależny status współpracy.
   Nie zdejmujemy automatycznie żadnego zakazu.

Nadawca w ręcznym procesie: `@artur_uluru_hair`, wyłącznie opis konfiguracji,
nie dowód logowania/autoryzacji tego konta.

## Bezpieczeństwo UI

- Synchroniczny ref blokuje dwa kliknięcia przed kolejnym renderem React.
- W trakcie operacji pola i akcje zmieniające payload są disabled; stan aria-busy.
- Ten sam payload po niepewnym wyniku zachowuje klucz idempotencji.
- Błąd odblokowuje formularz, pokazuje komunikat i odczytuje historię bez
  optymistycznego przypisania `sent`. Spóźniona odpowiedź zamkniętego profilu
  nie zastępuje aktualnie otwartego salonu.
- Profil CRM i historia są pobierane przy otwarciu; wejście na listę CRM odświeża dane.
  Nie uruchamiamy pełnego pakietu odczytów przy każdej zmianie strony.
- Starsze tekstowe audyty Meta są odczytywane bez JSON decode error i nadal
  stanowią wcześniejszy kontakt. Nie przepisano historycznych rekordów.

## Domyślnie OFF, bez migracji

`SALES_WORKFLOW_ENABLED` ma domyślne false; brak/pusta/nieparsowalna wartość
nie aktywuje modułu. Endpointy zwracają 404, panel ukryty. Nie zmieniono Render,
Blueprint ani produkcyjnych wartości flag. Nie zmieniono migracji/schematu.
Użyto istniejących Activity, Salon i opcjonalnego Task. Żaden transport wychodzący
Meta/Google/OpenAI nie jest dodawany ani aktywowany.

Wycofanie kodu: wyłączyć nową flagę po osobnej zgodzie operatora albo wrócić do
bazy PR #3 w osobno zatwierdzonym wydaniu. Zachować audyty i zadania; bez DELETE,
downgrade i kasowania historii. Przy cofaniu do kodu sprzed tej funkcji trzeba
uwzględnić brak obsługi nowych rodzajów kontaktu w jego raportach. Nie jest to
zweryfikowany plan produkcyjnego rollbacku i nie zamyka Issues #10–#13.

## Testy i dowody

Wszystkie nowe testy używają lokalnego PG17, fikcyjnych kont i danych. Nie użyto
produkcyjnych tokenów, eksportów ani bazy klientów.

Polecenia:

```sh
pytest -q --ignore=tests/test_salon_cleanup.py
npm run build --prefix frontend
python -m tests.ci_e2e
npm audit --prefix frontend
pip-audit -r requirements.txt --format=json --output=test-results/pip-audit-ci.json
```

DATABASE_URL dla testów wskazuje wyłącznie lokalne focus3_test. Istniejący runner
E2E tworzy i usuwa własną syntetyczną bazę focus3_ci_*. Nowy scenariusz uruchamia
się po niezmienionym production_browser_check. Nie pominięto testów aplikacji;
historyczne wyłączenie operatorskiego cleanup w workflow pozostaje bez zmian.
Po wznowieniu lokalnie: pełny backend408 PASS przed ostatnim testem wycofania;
34 PASS w końcowym zestawie celowanym (sales/guard/fixture), build PASS i dzień
sprzedaży Chromium/WebKit PASS. Nie przypisujemy tych wyników końcowemu CI.
Końcowe wyniki/numery workflow dokładnego SHA są publikowane w Issue #16 i Draft PR.
Nie przypisujemy wyniku starszego SHA do nowego commita.

Nowe obszary testów PostgreSQL: nieprawidłowe profile, snapshoty, brak potwierdzenia,
RBAC, dwa równoległe potwierdzenia z tym samym/różnymi UUID, zmiana payloadu przy
retry, opt-out, stara historia Meta, blokada kontaktu po rozmowie telefonicznej,
zadanie po odpowiedzi, kalendarz i domyślne OFF. Zachowano regresję szkoleń zespołu.

`tests/sales_day_browser.py`: Chromium desktop i WebKit iPhone 13, po 10 nowych
salonów, manager/handlowiec, discovery fixture, dubel, prior contact, błędny profil,
szkic, błąd HTTP503, dwa szybkie kliknięcia, blokady pól/Tab, spóźniona odpowiedź,
odmowa, podpisany inbound fixture/deduplikacja/bind/opt-out, zadanie, propozycja20min,
konflikt, potwierdzenie i zmiana terminu, raport/KPI i bezpośrednia kontrola PG.

W każdej kohorcie baza potwierdza 2 szkice, 2 deklaracje ręcznej wysyłki,
1 ręczną odpowiedź i 1 odmowę; 0 fikcyjnych API receipts. Dodatkowo kontrolowany
inbound jest fixture, nie prawdziwą odpowiedzią salonu. Oczekiwane KPI obejmują
całą syntetyczną bazę, dlatego druga kohorta pokazuje sumy kumulacyjne.
Lokalny przykład: [SYNTHETIC_RESULTS.json](SYNTHETIC_RESULTS.json).

Artefakty CI `verification-results`: sales-day.json, sales-day-contact-chromium.png,
sales-day-contact-webkit.png, sales-day-chromium.png, sales-day-webkit.png oraz
istniejące zrzuty i raporty PWA. Zrzuty zawierają tylko fikcyjne dane.

### Granice testów i blokada internetu

- Python httpx jest obsługiwany przez lokalne fixture; każda inna zewnętrzna
  próba jest odrzucana i zapisywana jako stały typ/kategoria providera.
- Guard socket/DNS blokuje wyjście z Pythona poza loopback. Nie zapisuje URL,
  query, nagłówków, dowolnych hostów, body ani sekretów.
- Playwright odrzuca zewnętrzne żądania; liczba takich prób musi być zero.
- Kontrola negatywna do never-connect.invalid jest zatrzymywana przed socketem,
  a osobny rejestr potwierdza, że brak detekcji powodowałby FAIL. Ten oczekiwany
  test nie zanieczyszcza rejestru normalnego dnia pracy.
- To guard użytych ścieżek testowych, nie deklaracja systemowego firewalla dla
  dowolnego natywnego procesu. Nie wykonujemy prób obejścia zabezpieczeń.
- **Profil fault-injection ma service_workers=block**, żeby WebKit nie omijał
  routingu Playwright przez fetch service workera. Osobny production_browser_check
  nadal testuje prawdziwy SW, PWA, cache i offline w obu silnikach bez tego ustawienia.
  Nie osłabiono CSP ani nie zwiększono timeoutów. WebKit to emulator, nie fizyczny iPhone.
- Cały milestone nie potwierdza OAuth na żywo, prawdziwych DM ani gotowości produkcji.

## Macierz funkcji

| Funkcja | Potwierdzony zakres / zależność |
|---|---|
| CRM, RBAC, duplikaty, lejek, agent reguł, lokalny planer, zadania i raport | działa end-to-end na lokalnym PG17 / syntetycznych danych |
| Discovery według miasta/promienia | tylko OSM mock w tym E2E; realna dostępność i kompletność zależą od źródła |
| Weryfikacja profilu i zdarzenie ręcznego kontaktu | wymaga operatora, podstawy kontaktu i zatwierdzenia właściciela; test to deklaracja syntetyczna |
| Podpisany webhook, inbox, bind, odpowiedź i opt-out | tylko fixture; wymaga Meta OAuth i dopuszczonej konfiguracji do użycia na żywo |
| Pierwszy niezamówiony DM przez API | nieobsługiwany; brak transportu, scrapingu i obchodzenia ograniczeń |
| Odpowiedzi API w uprawnionym oknie | nie zaimplementowano transportu; samo okno24h nie jest zgodą na wysyłkę |
| Produkcja / pełne wydanie | BLOCKED niezależnymi bramkami #10–#13; brak merge/deploy |

## Meta — źródła i ograniczenie weryfikacji

Próba odczytu 10.11.2026: oficjalne Messaging API Meta dla Facebook Login było
niedostępne w fetcherze, wersja Instagram Login zwróciła429. Strona oficjalnej
kolekcji Meta/Postman pokazała tylko powłokę dokumentacji. Nie twierdzimy, że
odczytano pełny aktualny kontrakt lub wyjątki.

- https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/messaging-api/
- https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/messaging-api/
- https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api

Istniejący adapter pozostaje przy Graph v26.0/Unified Login. Zachowano konserwatywny
zakres Issue #16: odbiorca inicjuje rozmowę, zwykłe okno odpowiedzi24h, wyjątki wymagają
osobnej weryfikacji. Nie traktujemy ręcznej wysyłki jako obejścia zgód/prawa/platformy.
Aktualny kontrakt musi zostać potwierdzony przed jakimkolwiek przyszłym transportem.

## Trzy następne luki — kolejność

1. Niezależny przegląd Draft PR i akceptacja syntetycznego przepływu przez właściciela;
   realne dane i rzeczywiste wysłanie pozostają poza testem.
2. Domknięcie dowodów wydania w #10–#13: integralność/konta, RPO, kopia/klucz,
   zachowany zgodny artefakt i handoff. To nie jest nowa prośba o operacje w tej sesji.
3. Dopiero osobno zatwierdzony etap Meta Development na autoryzowanym koncie testowym:
   aktualna dokumentacja, OAuth i inbound bez DM. Wysyłka wymaga jeszcze odrębnej zgody;
   cold DM przez API nie zostaje dopuszczony.

0 zmian produkcji, Render, env/sekretów/allowlisty, kosztów, merge/deploy, realnych DM,
Google, płatnego OpenAI lub Focus1.0/2.0. PR #3/#9/#15 nietknięte.

## Korekta po pierwszym CI

Dla53b00a7 workflow PR42889973198 przeszedł409 testów, obie przeglądarki i audyty,
ale push42889959040 nie zobaczył ostrzeżenia diagnostyki w WebKit. Pierwszy test
nie sprawdzał statusu odpowiedzi, więc sam timeout nie ustalał przyczyny HTTP.
Ograniczono nowy burst odświeżania do wejścia CRM i wzmocniono istniejący test:
wymagana odpowiedź200 oraz widoczne ostrzeżenie, bez retry i zwiększenia timeoutu.
Po zmianie lokalna dotychczasowa ścieżka Chromium/WebKit ponownie PASS. Końcowe CI
nowego SHA jest odrębnym dowodem w Issue16/PR17; wcześniejszy jeden SUCCESS go nie zastępuje.

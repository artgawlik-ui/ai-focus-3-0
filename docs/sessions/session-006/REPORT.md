# RAPORT AI FOCUS 3.0.4 — SESJA 006: RPO 60 minut

Data: 2 listopada 2026, Europe/Warsaw. **Decyzja: BLOCKED.**
**Decyzja właściciela zatwierdzona: maksymalna utrata danych RPO = 60 minut / 3600 s.**
Nie jest to zgoda na restore, eksport, zmianę planu, konfiguracji, zakup ani deploy.

## Wynik główny

Obecny płatny plan PostgreSQL **ma funkcję PITR**, więc nie wykazano potrzeby upgrade
wyłącznie dla RPO 60. Nie ma jednak dowodu aktualnego najnowszego skutecznego punktu
ani zakończonego testu ścieżki PITR w wymaganym oknie. **Nie potwierdzono osiągania RPO 60.**
Ostatni istniejący eksport jest zbyt stary, by samodzielnie spełniać to wymaganie.

## Fakty z nowego odczytu

Źródło: oficjalne GET API, istniejąca autoryzacja CLI; provider-readonly.json.
Obserwacja od 2026-11-01 23:12:55 UTC, tj. 2 listopada 00:12:55 Warszawa.
- ai-focus-3-0-db / dpg-dbh1b0gm7kps73f0p2m0-a, status available, PostgreSQL 17,
  **compute plan 0.1c-256mb**, 1 GB dysku, Frankfurt, HA=false, pusta publiczna allowlista.
- GET recovery: HTTP 200, **recoveryStatus AVAILABLE**, startsAt=2026-10-29T06:32:47Z.
  Zwrócone klucze tylko recoveryStatus/startsAt. Brak endsAt, latest recoverable timestamp
  i metryki lag WAL. Nie wyliczamy najnowszego punktu z czasu odpowiedzi HTTP.
- Najnowszy eksport nadal **2026-11-01 18:25 UTC / 19:25 Warszawa**; wiek przy obliczeniu
  **17 278 s = 4 godz. 47 min 58 s**, limit 3600 s przekroczony.
  TOC z sesji 005: 18:27:29 UTC; użycie tego czasu również daje ponad 60 minut.
- API owner ujawnia tylko metadata tożsamości/typu workspace, nie plan billingowy.
  **Nie potwierdzono**, czy workspace jest Hobby czy Pro. Nie wnioskujemy z startsAt.
- Brak zmian API/konfiguracji, nowych eksportów i instancji.

## Aktualna dokumentacja i ograniczenia

Odczyt HTTP 200 i SHA w official-references.json:
- https://render.com/docs/postgresql-backups.md
- https://render.com/docs/compute-plans.md
- https://render.com/pricing
- https://render.com/docs/cronjobs.md

Dokumentacja: Render stale kopiuje płatne bazy na potrzeby PITR. Okno zależy od
**workspace plan**, nie od samego compute: Hobby 3 dni, Pro+ 7 dni. Upgrade nie
uzupełnia wstecz brakujących 7 dni. Free compute nie ma managed recovery.
Obecny compute 0.1c-256mb jest płatny, 0.1 CPU / 256 MB, max 100 połączeń;
wyższy compute zmienia zasoby/limit, nie stanowi dowodu krótszego opóźnienia archiwizacji.

Dokumentacja zabrania wyboru punktu z **ostatnich 10 minut**. To minimalny dystans
wyboru, **nie gwarantowany maksymalny lag 10 minut ani SLA RPO**. Pozwala rozważać
punkt np. sprzed 30 minut, ale trzeba potwierdzić, że jest faktycznie dostępny i działa.
AVAILABLE + startsAt nie zamyka takiego dowodu. Logiczne eksporty Render są przechowywane
7 dni; czas przechowywania nie jest częstotliwością tworzenia ani RPO.

Próba odczytu strony referencji API get-postgres-recovery-info zwróciła 404;
nie oparto na niej wniosków. Rzeczywiste klucze odpowiedzi GET są odczytanym dowodem,
a aktualne ograniczenia produktu pochodzą z dostępnej oficjalnej dokumentacji.

## Trzy poziomy, których nie utożsamiamy

| Dowód | Stan | Co potwierdza |
|---|---|---|
| Funkcja PITR na płatnym compute | PASS dokumentacji i metadata | plan nie wyklucza RPO 60 |
| API AVAILABLE i startsAt | PASS odczytu | deklarowana gotowość recovery i dolna granica |
| Latest skuteczny punkt ≤60 min | **NIEPOTWIERDZONY** | brak górnej granicy/lag/konkretnego punktu |
| Rzeczywisty test PITR do punktu w oknie RPO | **NIEWYKONANY** | bez niego nie stwierdzamy skuteczności tego kanału |
| Eksport logiczny z 19:25 | PASS restore snapshotu, **FAIL jako samodzielne RPO 60** | sesja 005: 17 tabel/23 rekordy/004, lecz stary punkt |
| Trwała niezależna szyfrowana kopia ≤60 min | **NIEPOTWIERDZONA** | aktualny dzienny offsite nie spełnia wymagania |

Test właściciela i niezależny test eksportu z sesji 005 zachowują ważność dla tego
snapshotu. Nie powtarzano ich, nie pobierano kopii ani nie wykonywano nowego restore.
Poprawny restore dumpa nie testuje odtwarzania WAL/PITR. RPO nie jest RTO i nie zależy
od tego, jak szybko zakończył się lokalny restore.

## Czy potrzebna jest nowa kopia?

**Tak, jeśli kopia logiczna ma być samodzielnym punktem gwarantującym RPO 60**:
obecna jest za stara. Nie utworzono nowego eksportu, bo zgoda na RPO nie jest zgodą
na operację. Pojedynczy nowy eksport rozwiązałby wiek tylko chwilowo, nie ciągłe RPO.
Jeżeli PITR zostanie udowodniony i monitorowany, może być podstawową ścieżką RPO,
a niezależna kopia ma odrębną rolę bezpieczeństwa/retencji. RPO dla utraty całego
konta/Render wymaga niezależnej równie świeżej ścieżki albo jawnego uzgodnienia zakresu;
nie zakładamy takiego wyjątku od zatwierdzonej polityki.

Obecny scripts/offsite_backup.py: harmonogram 86400 s, retry 3600 s po błędzie,
OFFSITE_BACKUP_ENABLED dotychczas OFF. **Nie spełnia RPO 60 po samym włączeniu.**
Godzinny interwał + czas backupu/uploadu także może przekroczyć 60 minut.
scripts/backup.py używa SHARE LOCK na wszystkich tabelach, trzyma dump w RAM;
częste uruchamianie grozi blokowaniem zapisów i presją pamięci 512 MB usługi.
Nie zmieniano tego kodu/harmonogramu/flag w tej sesji.

## Najprostsze rozwiązanie do zatwierdzenia

**Rekomendacja: pozostawić obecny płatny compute i najpierw zweryfikować istniejący PITR.**
1. Odczytowo w Render → baza → Recovery sprawdzić realne okno i punkt np. now−30 min.
   W razie braku metryki uzyskać od Render latest recoverable timestamp/lag i potwierdzenie
   ograniczeń/gwarancji. Nie wysłano wiadomości do supportu i nie uruchamiano formularza recovery.
2. Po osobnej zgodzie na koszt/operację: jednorazowy PITR do **nowej izolowanej bazy testowej**,
   nigdy restore w miejsce produkcji ani zmiana DATABASE_URL. Potwierdzić target/replay,
   spójność 004/17 tabel/danych i rzeczywiście odtworzony punkt w RPO. Sam brak zmian w
   23 rekordach nie dowodzi świeżości. Operacja w tej sesji zabroniona i niewykonana.
3. Zatwierdzić źródło metryki/nadzór i reakcję przed 60 min. Samo monitorowanie AVAILABLE
   nie jest monitorem RPO. Proponowane warning 30 / critical 45 min i obserwacja co 5 min
   wymagają zatwierdzenia i implementacji, nie są obecnie działającą funkcją.

Jeżeli tej ścieżki nie da się potwierdzić albo potrzebna niezależność od Render,
przygotować oddzielnie backup np. co 15 min z trwałym szyfrowanym magazynem, budżetem
wykonania, retry i alarmami. Najpierw poprawić snapshot/locking i zmierzyć obciążenie;
nie sprzedawać samego harmonogramu jako gwarancji RPO. Szczegóły RECOVERY_PROCEDURE.md.

## Koszty — tylko wycena, nic nie kupiono

Cennik odczytany 2 listopada, USD przed podatkami i ponadlimitowym zużyciem:

| Wariant | Przewidywany koszt | Wniosek |
|---|---|---|
| Użycie obecnego PITR | 0 dodatkowego abonamentu względem obecnej płatnej bazy | brak potrzeby upgrade tylko dla RPO 60; dowód nadal wymagany |
| Obecny compute PostgreSQL 0.1c-256mb | 6 USD/mies., 1 GB wliczony | obecne koszty, nie nowy zakup; nie zweryfikowano całej faktury |
| Tymczasowa recovery DB tego samego typu | dodatkowo 6 USD/mies. przy pozostawieniu; prorata sekundowa | przy 30-dniowym miesiącu ok. 0,0083 USD/h, ok. 0,20 USD/24h compute; UI musi potwierdzić plan i dysk |
| Więcej storage | 0,30 USD/GB/mies. ponad wliczone 1 GB | zależy od wybranej pojemności/zużycia i czasu naliczania |
| Workspace Hobby → Pro | 25 USD/mies. + compute wg obecnego cennika | zwiększa okno 3→7 dni, nie dowodzi niższego RPO; aktualny tier nieznany |
| Compute 0.5c-1g | 19 USD/mies., +13 względem 6 | więcej zasobów; nie jest uzasadnionym rozwiązaniem samego braku dowodu RPO |
| Opcjonalny osobny backup cron 0.5c-512mb | 0,00016 USD/min aktywności, min. 1 USD/mies./cron | plus magazyn, requesty, transfer i ewentualne klucze; nie utworzono |

Dla ilustracji: co 15 min, 2 min/run, 30 dni to 5760 min, ok. 0,92 USD, więc z minimum
ok. 1 USD compute; czas wykonania nie został zmierzony i wycena nie jest ofertą końcową.
Nie wskazano dostawcy/regionu magazynu, więc jego kosztu nie wyceniono jako stałej kwoty.
Bez tego nie ma zgody na uruchomienie nowej infrastruktury. Zmiana compute może powodować
przerwę; HA również nie zastępuje PITR i nie gwarantuje ochrony przed logicznym DELETE.

## Zaktualizowane kryteria READY / BLOCKED

**RPO gate może mieć PASS dopiero po łącznym potwierdzeniu:**
- wymaganie właściciela 3600 s zapisane i zakres awarii określony;
- bieżący, wiarygodny skutecznie utrwalony/odtwarzalny punkt o wieku ≤3600 s;
- izolowany zakończony test właściwej ścieżki z dowodem target/replay i integralności,
  bez utożsamiania starego dumpa z PITR;
- trwały dostęp do kopii/kluczy, uzgodniona retencja i nadzór świeżości/reakcja na degradację;
- pozostałe kryteria wydania SQL/kont/rollback/workera oraz checks dokładnego SHA spełnione.
Brak dowolnego krytycznego dowodu -> BLOCKED. AVAILABLE, paid tier i stary poprawny
restore są dowodami częściowymi. Aktualny gate pozostaje **BLOCKED**.

## Procedura, źródła i wyniki

RECOVERY_PROCEDURE.md: szyfrowanie AES-256-GCM/scrypt, niezależny manager klucza,
proponowana retencja 30 dni, odzyskiwanie klucza i izolowany restore. Nazwy zmiennych,
nie wartości. Wszystkie propozycje aktywacji pozostają niezrealizowane.
Nowe kontrole to GET i audyt źródeł/kodu; nie zmieniono aplikacji/dependencies, nie
powtarzano niezmienionych lokalnych testów restore/backup. CI nowego HEAD wykona
standardową syntetyczną regresję; 11 testów operatorskiego cleanup nadal wykluczonych.
Polecenia i źródła w evidence.json, official-references.json.
Bazowy PR HEAD d58b34d, Draft/niepołączony; kryteria zapisano commitem a750598.
Pozostałe pliki/commit raportu: git log; zakres w diff-base.txt.

**Nie wykonano:** produkcyjnego restore/PITR, nowego eksportu Render, pobrania nowych
kopii, zmiany planu/konfiguracji/harmonogramu, zakupu zasobów, merge/deploy, restartu,
produkcyjnych migracji/DELETE/cleanup, aktywacji Meta/DM. Nie ujawniono sekretów i URL
podpisanych. Focus 1.0/2.0 nietknięte. Koszt nowych zasobów w tej sesji: 0.

Wznowienie: odczytać aktualne HEAD/checks, respektować RPO 60, nie tworzyć testowej
recovery DB bez nowej zgody. Najpierw potwierdzić najnowszy punkt i uzgodnić test/koszt.
Nie wymagać ponownego logowania, skoro Render API działa; blokada SQL jest odrębna.
Pozostaje szacunkowo **5 sesji podstawowych + ≥1 DM**, bez zmniejszania za niezamkniętą
bramkę operacyjną. Nie deklarujemy działania w tle po zakończeniu sesji.

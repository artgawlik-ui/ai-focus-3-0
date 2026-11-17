# RAPORT AI FOCUS 3.0.4 — SESJA 005

Data sesji: 1 listopada 2026, Europe/Warsaw. **Decyzja: BLOCKED.**
Odtwarzalność konkretnego eksportu zamknięta dowodami; aktualna zgodność produkcji,
pełna gotowość recovery i okno pracy workera nadal wymagają kontroli/decyzji.

## Punkt startowy i zakres

Gałąź fix/3.0.4-meta-validation; PR #3 Draft/open/bez merge.
Bazowy HEAD bc78b7cb4dce2fdf2864047301aacb5ce886433a; obie kontrole dla tego SHA
41357975518 (PR) i 41357970550 (push) ponownie odczytane success. Bazowe testy: 140,
build/Chromium/WebKit/audyty PASS z sesji 004; nie przedstawiamy ich jako nowych testów.
22fe3f5 zapisał kryteria przed pracą; 84e8bed dodał generator SELECT/testy.
Dokumentacja/dowody tego katalogu w kolejnym commicie, identyfikator przez git log.
Nie zmieniano schematu ani kodu aplikacji produkcyjnej. Jedyny head Alembic: 004;
brak zmian modeli/migracji względem origin/main d15265b.

## Dowód właściciela — przyjęty z podanym zakresem

**OWNER_VERIFIED:** 1 listopada pobrano rzeczywisty eksport Render, odtworzono lokalnie
na PostgreSQL 17.11 i potwierdzono 17 tabel, 23 rekordy i Alembic 004.
To potwierdza wynik testu snapshotu. Nie znamy z samej relacji SHA/ID tego pliku,
aktualności względem produkcji ani polityki trwałego szyfrowanego przechowywania.
Nie utożsamiamy go automatycznie z plikiem niezależnie pobranym w tej sesji tylko
dlatego, że liczby i dzień są zgodne.

## Nowy niezależny odczyt i restore istniejącego eksportu

API GET /postgres/{id}/export zwróciło 3 istniejące eksporty; najnowszy:
- etykieta eksportu **2026-11-01 18:25 UTC / 19:25 Warszawa**;
- TOC start dumpa **18:27:29 UTC / 19:27:29 Warszawa**, nie utożsamiany z każdą chwilą
  transakcyjnego stanu bazy ani metadanymi creation time eksportu;
- archiwum **8 996 bajtów**, SHA-256
  `c7fcd97d374cd3d3696b9ea35a1a99dc83a944e460c890131ad5966d97232a8c`;
- drugą kontrolę wykonano 22:53:30 UTC / 23:53:30 Warszawa; wiek etykiety eksportu
  **4 godziny 28 minut 30 sekund**, nie gwarancja spełnienia nieustalonego RPO;
- CRC gzip, TOC, 17/17 liczności/hashów źródłowego COPY i odtworzenia zgodne;
- **17 tabel, 23 rekordy łącznie z metadanymi, revision 004**;
- TOC wskazuje źródłowe PostgreSQL/pg_dump 17.11. Restore do nowego lokalnego PostgreSQL
  major 17, bez aplikacji, agentów, schedulera i sieci, Meta OFF; zgodność ORM/ograniczeń/indeksów;
- kontener i wszystkie jawne kopie tymczasowe usunięte. Oryginalnych eksportów nie zmieniono.

Szczegóły: backup-observation.json i restore-verification.json.
To nowy dowód odtwarzalności **tego eksportu**, zgodny z liczbami właściciela.
Nie przeprowadzono funkcjonalnych testów aplikacji na rzeczywistych danych.
Eksport pobrano oddzielnym klientem HTTP bez nagłówka Render Authorization; podpisany
URL/klucz były tylko w pamięci. Do repo trafiły wyłącznie metadata/agregaty/hashe.
Nie zachowano nowej jawnej kopii ani nie skonfigurowano trwałego zaszyfrowanego magazynu.
Nie twierdzimy, że usunięcie plików jest certyfikowanym wymazaniem fizycznego nośnika.

## Recovery i rollback — rzeczywisty odczyt bez uruchamiania

GET recovery: **recoveryStatus AVAILABLE**, startsAt=2026-10-29T06:32:47Z.
Odpowiedź nie zawiera endsAt; nie ustalamy pełnej górnej granicy ani RPO/RTO z tego pola.
PITR nie został wykonany, nie utworzono instancji ani płatnego restore.

GET deploys ponownie potwierdził live **d15265b26524d594bdbcb4bc6b63fcbc398a1424**,
**dep-dbjhl6jbc2fs73crj65g**. To punkt powrotu po przyszłym wydaniu. API nie zwraca
rollbackAvailable/rollbackEligible; lista deployów nie dowodzi retencji artefaktu.
Reguły Render sprawdzone w sesji 004: rollback wymaga zachowanego artefaktu, używa części
ustawień target deployu, nie cofa DB/dysków. Nie klikano Rollback ani nie testowano rebuild.
Dokumenty źródłowe: https://render.com/docs/rollbacks.md oraz dowód odczytu w session-004.

Aktualny odczyt metadata PostgreSQL: available, major 17, Frankfurt, publiczna allowlista
pusta. Brak grantów TCP w środowisku wykonawczym; nowego wewnętrznego kanału nie skonfigurowano.
Odmowa hosted MCP z sesji 004 pozostaje aktualną blokadą z niezmienioną przyczyną;
nie powtarzano identycznej zewnętrznej próby ani nie obchodzono zabezpieczeń.
Render API/CLI jest uwierzytelniony: brakuje kanału SQL, nie hasła lub nowego tokenu.

## Macierz zamknięcia blokad

| Blokada | Wynik w sesji 005 | Co pozostaje |
|---|---|---|
| Czy rzeczywisty eksport daje się odtworzyć | **ZAMKNIĘTA DLA SNAPSHOTU** | OWNER_VERIFIED i niezależny restore 17/23/004 |
| Czy eksport jest dostępny do pobrania | **PASS aktualnego odczytu** | odczyt/pobranie istniejącego pliku; przyszła retencja niegwarantowana |
| Czy eksport odpowiada bieżącej produkcji | **OPEN** | nowe SELECT-y i zgodny manifest/uzasadnione zmiany; RPO nieustalone |
| Produkcyjny Alembic/konta/sesje/integralność | **OPEN** | aktualny zatwierdzony wewnętrzny SQL |
| Trwała niezależna szyfrowana kopia i klucz | **OPEN** | magazyn, retencja, odzyskanie klucza i polityka usunięć; offsite aplikacji OFF |
| Identyfikacja aktualnego punktu rollback | **PASS metadata** | d15265b/dep-dbjhl6jbc2fs73crj65g potwierdzone |
| Gwarantowana dostępność obrazu/środowiska rollback | **OPEN** | weryfikacja przed wydaniem; API nie ma osobnej eligibility flag |
| Zapisane flagi Meta OFF | **PASS metadata** | ponowna kontrola runtime/target deployu w oknie wydania |
| Globalny brak automatycznych zapisów | **NIE ZAPEWNIONY** | AGENT_V2 nie zatrzymuje kolejki ani retencji; decyzja o trybie pracy |
| Zgoda na merge/deploy | **NIEUDZIELONA** | osobna decyzja po zamknięciu krytycznych warunków |

Nie wymagamy ponownego dowodzenia odtwarzalności tego samego niezmienionego pliku bez
przyczyny. Test restore **nowej** kopii lub weryfikacja jej aktualności to inna kontrola.
Nowy odczyt SQL jest niezbędny; 23 rekordy nie są stałą oczekiwaną liczbą w działającym CRM.

## SELECT-y i testy

scripts/release_selects.py nie ma połączenia z bazą ani funkcji DML. Renderuje
SELECTS.sql (parametry psycopg) i SELECTS.psql (prywatne prompt-y psql).
Cztery zapytania: baseline PG/revision/tabele/validated constraints; agregaty kont/sesji;
count/SHA wszystkich 17 tabel; kolejka/inbox/kandydaci retencji i anomalie dat.
Szczegóły warunków/algorytmu/prywatności w RELEASE_PLAN.md.

Lokalny PostgreSQL syntetyczny: **3 passed**, 0 failed/errors/skipped (1,82 s).
Sprawdzono read-only/repeatable-read, 004/17 tabel, konta aktywne/nieaktywne i brak ID
w wynikach, stabilność hashów, brak DML w zapytaniach, format prywatnych parametrów,
a także granicę 7 dni dla retencji na tej samej dacie (ważna różnica T/odstęp w ISO).
Nie wykonano tych SELECT-ów na produkcji. Brak metryki procentowego code coverage.
Końcowy CI nowego SHA uruchamia regresję aplikacji, build, Chromium/WebKit i audyty;
11 testów operatorskiego cleanup nadal wykluczonych według obowiązującego zakazu.
Wynik końcowego HEAD należy odczytać w Checks PR #3; stary PASS nie jest jego substytutem.

## Napotkane problemy i naprawa

Pierwszy restore miał wynik integralności PASS i usunięty kontener, ale agregator raportu
odczytał count z niewłaściwego poziomu JSON (KeyError). Nie uznano tego wyniku za zamknięty
raport; skorygowano odczyt restored_copy.count i powtórzono kontrolę. SHA eksportu zgodny.
Pierwszy test SELECT ujawnił niejednoznaczny typ parametru przy IS NOT NULL; dodano ::text.
Doprecyzowano też porównania dat retencji przez timestamptz i test granicy dnia.
Po poprawkach 3/3 testy zielone. Nie było operacji na danych produkcyjnych ani wycieku.

## Ryzyko wdrożenia i dokładne działania właściciela

Plan z punktami STOP i kontrolami po wdrożeniu: RELEASE_PLAN.md.
Meta OFF nie zatrzymuje maintenance; przy rolling deploy mogą równolegle pracować stare
oraz nowe workery. Fingerprinty mogą się zmieniać przez joby, sesje i retencję niezależnie
od zmiany kodu. Nie wolno zignorować tabel lub przyjąć zgodności samych liczności.

Właściciel musi zatwierdzić lub zapewnić:
1. **Wewnętrzny READ ONLY** istniejącej usługi i transfer zatwierdzonego pakietu SELECT,
   prywatnie zatwierdzone ID właściciela/technicznego konta; ograniczony grant wykonawcy.
   Alternatywnie odczyt we własnym Render Shell. Nie otwierać publicznej allowlisty.
2. **Akceptowalne RPO/aktualność**: czy odtwarzalny eksport z 19:25 jest dopuszczalny po
   porównaniu z bieżącą bazą, czy potrzebny jest nowy eksport w uzgodnionym oknie.
   Sesja 005 nie udziela zgody na utworzenie nowego eksportu/zmiany harmonogramu.
3. **Trwały szyfrowany magazyn, klucz i retencję**, bez przekazywania sekretów w rozmowie;
   niezależnie od deklaracji AVAILABLE/PITR. Nowy koszt wymaga wcześniejszej zgody.
4. **Tryb pracy workera**: zaakceptowane szkice/retencja i rozliczenie driftu albo osobno
   zatwierdzone okno bez zapisów obejmujące API, kolejkę i maintenance. OFF AGENT_V2 nie wystarcza.
   W tej sesji nie pauzowano procesów ani nie zmieniano konfiguracji.
5. **Potwierdzenie dostępności artefaktu rollbacku** i jego środowiska w oficjalnym panelu,
   bez wywołania rollbacku; jeśli niedostępny, osobna zgoda na plan rebuild, nie automatyczny fallback.
6. **Osobną decyzję o merge/deploy konkretnego SHA Meta OFF**, dopiero po spełnieniu STOP-ów.
   Żaden z powyższych punktów nie upoważnia do cleanup, migracji, restartu lub Instagrama.

Jeśli ograniczony dostęp zostanie udostępniony, techniczne odczyty wykona agent;
nie wymagamy ręcznych komend, które można wtedy wykonać bezpiecznie samodzielnie.

## Bezpieczeństwo i wznowienie

Wykonano wyłącznie produkcyjne GET metadata/pobranie istniejącego eksportu. Brak produkcyjnych
zapytań zapisujących, migracji, DELETE, cleanup, restartu, merge/deploy, zmian konfiguracji,
uprawnień/sieci/sekretów. Nie uruchomiono aplikacji/agentów na rzeczywistej kopii ani Meta/DM.
Nie utworzono eksportu, instancji, płatnego restore ani magazynu. Oryginalny eksport niezmieniony.
Focus 1.0/2.0 nietknięte. Zmiany tylko tego repozytorium; diff-base.txt względem d15265b.

Pozostaje **5 sesji podstawowych + ≥1 DM**. Zamknięto dowód snapshotu, ale nie pełną
operacyjną bramkę recovery/aktualnej produkcji, więc licznik nie jest zmniejszany.
Wznowić od nowego HEAD/checks i zatwierdzonego kanału SQL, nie powtarzać bez potrzeby
restore tego samego SHA. Rozdzielać timestamp eksportu, jego odtwarzalność i aktualny stan.
Nie działamy w tle po zakończeniu sesji.

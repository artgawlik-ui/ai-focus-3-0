# Przygotowanie usunięcia salonu testowego — operacja BLOCKED / niewykonana

Właściciel potwierdził, że jedyny salon w pierwotnym eksporcie powstał podczas testowania Focus 3.0. Przygotowano konkretny plan, kopię i skrypty. **Nie wykonano produkcyjnego DELETE, COMMIT, merge, deploy ani aktywacji Meta.**

## Identyfikacja i ograniczenie odczytu

Odczyt SQL aktualnej produkcji przez Render MCP ponownie zablokowała pusta allowlista; środowisko nadal nie ma grantów TCP do SSH. Nie zmieniono zabezpieczeń ani konfiguracji. **Nie przedstawiamy odczytu odtworzonej migawki jako odczytu bieżącej bazy.**

Aby nie opierać planu wyłącznie na starej kopii, utworzono nowy eksport bezpieczeństwa przez oficjalne POST /postgres/{id}/export (202), zgodnie ze zleceniem przygotowania kopii. Nie utworzono nowej instancji ani płatnego restore. Render nadal przechowuje wcześniejszy eksport; jego ponownie pobrany SHA-256 jest identyczny:

- oryginał: `2026-11-01T12:41Z`, SHA-256 `093ab561995be1f5af8383610b7b725113950a592a466ed14b5a348ad4a4f42d`;
- nowy backup: `2026-11-01T13:36Z` (14:36 Europe/Warsaw), dump TOC **13:37:51 UTC**;
- nowy SHA-256: `fc99b4568c04c13fae9724ffadd85cc50c153d6709ce98e99f979e87cb816be2`.

Obie kopie odtworzono lokalnie w kontenerze PostgreSQL 17 **bez sieci, portów, host mounts, aplikacji, workerów i logów SQL**, ze wszystkimi flagami Meta OFF. Oryginał miał dokładnie jeden salon. Jego ID i pełny zakres pięciu tabel, wraz z hashami każdego zbioru rekordów, są **identyczne w nowej kopii**. Nie wybierano klienta przez nazwę, LIKE, priorytet ani status.

**Salon: `d68c81ad-6e39-44df-aa95-f45f922189c4`.** To dowód tożsamości i niezmienności na punkt nowego eksportu. Bieżący stan przed rzeczywistym usunięciem musi być ponownie sprawdzony w transakcji; zmiana choćby jednego rekordu spowoduje odmowę.

## Dokładny proponowany zakres

| Tabela | Rekordy do usunięcia | Kryterium |
|---|---:|---|
| salons | **1** | wyłącznie wskazany ID i zgodny hash całego rekordu |
| activities | **8** | dokładne ID z manifestu oraz salon_id = wskazany ID |
| appointments | **1** | dokładny ID i wskazany salon_id |
| jobs | **3** | dokładne ID, salon_id, zgodne hashe; brak queued/running |
| integration_links | **0** | pozostają puste dla tego salonu; nowy rekord zablokuje skrypt |
| **Razem** | **13** | zamknięta lista, bez CASCADE |

ID dzieci i fingerprinty: [scope-manifest.json](scope-manifest.json). Nie publikuje się treści notatek, komunikacji, kontaktów, haseł i tokenów.

**Poza zakresem:** wszystkie konta i sesje (w tym właściciel i wyłączone konto techniczne), próby logowania, szkolenia, metadane Alembic, wszystkie tabele Meta i dane innych klientów. Brak powiązanych konwersacji Meta w obu migawkach. Nie wykonuje się operacji w Instagramie, Google Calendar ani Livespace. Usunięcie lokalnego rekordu wizyty nie jest anulowaniem zdarzenia w zewnętrznym kalendarzu.

## Kopia i sprawdzenie odtwarzania

Nowy eksport 8 994 B zweryfikowano CRC, TOC i SHA-256. Odtworzenie: 17 tabel, Alembic 004, wszystkie liczności/fingerprinty zgodne z eksportem. Nie zmieniano oryginalnych danych eksportów.

Dodatkowo przygotowano **szyfrowaną kopię świeżego archiwum** oraz **szyfrowany pakiet celowanego odtworzenia 13 rekordów**:

- lokalnie `.render-auth/salon-cleanup/fresh-backup.enc` — 9 046 B;
- lokalnie `.render-auth/salon-cleanup/undo.enc` — 25 664 B;
- format FOCUS3C1: AES-256-GCM + scrypt, oddzielny salt/nonce i AAD archive/undo;
- obie kopie 0600, katalog prywatny 0700, poza Git; użyto istniejącego prywatnego powiązania klucza kopii, bez ujawniania wartości;
- deszyfrowanie i hash archiwum sprawdzono **przed** odtworzeniem; pakiet undo również przeszedł weryfikację encrypt/decrypt;
- surowe pobrania i rozpakowane katalogi usunięto, kontener z tmpfs został usunięty. Pozostają wyłącznie chronione pliki zaszyfrowane i bezpieczne raporty.

Render zachowuje niezależny nowy eksport pod istniejącą ochroną konta. Przed faktyczną operacją należy potwierdzić aktualność kopii oraz bezpieczną dostępność materiału odzyskiwania i klucza poza ulotną sesją roboczą. Nie przenoszono kopii do nowego płatnego storage i nie konfigurowano sekretów produkcyjnych.

## Transakcyjny SQL

[DELETE_TEST_SALON.sql](DELETE_TEST_SALON.sql) **domyślnie kończy się ROLLBACK**. Nie jest automatycznym zadaniem aplikacji. Nie ma funkcji/endpointu/CLI automatycznie wykonującego COMMIT.

Przed DML skrypt sprawdza bazę `ai_focus_3_0_db`, PostgreSQL 17 i revision 004, zgodność katalogu tabel/kolumn/ograniczeń/indeksów, brak własnych triggerów/rules/RLS w modyfikowanych tabelach, niedozwolonych kaskad i obcych zależności. Blokuje zakres przy dowolnym połączeniu Meta lub aktywnym zadaniu agenta. Porównuje pełne listy ID i hashe całych rekordów, nie tylko liczbę salonów.

SERIALIZABLE oraz krótkie blokady tabel `salons`, `activities`, `appointments`, `jobs`, `integration_links`, `meta_conversations` zabezpieczają przed wyścigiem podczas sprawdzania i modyfikacji. Mogą chwilowo wstrzymać zapisy CRM; lock_timeout 2 s, statement_timeout 10 s i idle timeout 15 s powodują przerwanie zamiast nieograniczonego oczekiwania. Nie wyłącza się usługi. Usuwanie odbywa się dzieci → salon, każde DELETE sprawdza dokładną liczbę wierszy. Fingerprint pozostałych danych przed/po musi być identyczny.

Jeśli pojawi się nowy rekord zależny, zmieni się treść/wersja, zniknie salon, pojawi się inny schemat, powiązanie Meta lub zadanie w toku — **całość abortuje**. Nie wolno „dopasowywać” hashy i liczności do zmienionych danych bez ponownego przeglądu i zatwierdzenia zakresu.

## Testy

- Rzeczywista odizolowana kopia: próba przygotowanego DELETE zakończona obowiązkowym ROLLBACK; **wszystkie 17 fingerprintów pozostało identycznych**. Produkcja nie była celem tej próby.
- Syntetyczna baza: test COMMIT usunięcia dokładnego zakresu i celowanego undo, zachowanie drugiego klienta/kont, odrzucanie zmienionego salonu/dziecka, nowego dziecka, Meta linku, działającego joba, nieznanego FK/kaskady, triggera i kolizji odtworzenia; weryfikacja AEAD przy złym kluczu/zmianie typu/uszkodzeniu.
- Pełny backend: **116 passed, 0 failed/errors/skipped**, wobec poprzednich 105. Testy automatyczne wyłącznie na danych syntetycznych i lokalnym PostgreSQL. Nowy backup służył tylko odizolowanej kontroli integralności i próbie z ROLLBACK.
- Wynik końcowego CI dostępny w Draft PR #3. Brak nowych migracji, zależności i funkcji transportu.

## Wycofanie

**Przed COMMIT:** ROLLBACK, przerwanie połączenia lub błąd guardów wycofuje wszystkie usunięcia. Ten wariant jest domyślny i został sprawdzony na rzeczywistej kopii.

**Po zatwierdzonym COMMIT:** zwykły SQL ROLLBACK nie cofnie operacji. Odtwarzanie wyłącznie wybranych 13 rekordów z zaszyfrowanego pakietu: salon przed dziećmi, bez upsert/overwrite, z kontrolą schematu, wolnych identyfikatorów, istniejącego rodzica użytkownika i hashy. Nowe dane i kolizje przerywają odtworzenie; nie wolno nadpisywać późniejszych rekordów. Pakiet zawiera dane, więc jego odszyfrowanie i wykonanie tylko w zatwierdzonym kanale bez logowania treści SQL/danych. Generowany undo również domyślnie kończy się ROLLBACK. Trwałe undo sprawdzono wyłącznie na danych syntetycznych, nie na produkcji.

Nie odtwarzać całej produkcyjnej bazy na starą migawkę jako automatycznego undo — utraciłoby to późniejsze zmiany innych rekordów. PITR/new instance/cutover pozostają osobną, potencjalnie płatną operacją wymagającą zgody.

## Status i następne wymagane decyzje

**Przygotowanie: GOTOWE DO PRZEGLĄDU. Wykonanie na produkcji: BLOCKED.**

1. Potrzebny zatwierdzony wewnętrzny kanał do aktualnego odczytu SQL. Nie otwierano allowlisty, nie zmieniano sieci, danych i sekretów. Aktualny odczyt nie został zastąpiony twierdzeniem o niezmienności bieżącej produkcji.
2. Po udostępnieniu kanału agent odczyta bieżący zakres w READ ONLY i porówna go z manifestem. Nieścisłość oznacza stop i nowy raport, bez usunięcia.
3. Właściciel zatwierdza **konkretny ID i powyższe 13 rekordów**, aktualną kopię oraz procedurę wycofania. Potwierdzenie, że dawny salon był testowy, nie zostało uznane za zgodę na produkcyjny COMMIT.
4. Dopiero po zgodzie można wykonać odpowiadający zatwierdzonemu planowi wariant transakcji, a następnie odczytowo sprawdzić wynik i zachowanie pozostałych danych. Nie wymaga to merge/deploy/aktywacji Meta; nie wykonano żadnej z tych czynności.

Focus 1.0 i 2.0 oraz inni klienci nie byli przedmiotem żadnego zapisu. Jedyna zmiana w Render to utworzenie zleconego nowego eksportu bezpieczeństwa, bez nowej instancji i bez kasowania starego eksportu.

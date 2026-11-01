# Procedura recovery i szyfrowanego magazynu — przygotowana, niewdrożona

## Rozdzielenie trzech dowodów

1. AVAILABLE: provider zgłasza możliwość recovery. Nie dowodzi najnowszego punktu,
   skuteczności konkretnego restore, spójności aplikacji ani opóźnienia archiwizacji WAL.
2. Punkt odzyskiwalny: potrzebny wiarygodny czas/LSN najnowszych skutecznie utrwalonych
   danych i możliwość wybrania punktu o wieku ≤3600 s. startsAt nie jest tym punktem.
3. Skuteczne odzyskanie: zakończony, izolowany PITR do zatwierdzonego czasu w oknie RPO,
   dowód rzeczywiście odtworzonego czasu/replay/LSN oraz poprawne 004/17 tabel/relacje/dane.
   Odtworzenie starego logicznego dumpa nie zastępuje testu ścieżki PITR/WAL.

RPO nie jest RTO: czas trwania recovery nie jest wiekiem odzyskanych danych.
Nie traktować porównania 17 tabel/23 rekordów jako dowodu odzyskania świeżych commitów,
zwłaszcza gdy w źródle nie było ruchu. Wykorzystać istniejące zatwierdzone ślady transakcji
lub dowód replay providera; nie dopisywać markerów do produkcji bez osobnej zgody.

## Najprostsze rozwiązanie do zatwierdzenia: obecny PITR, bez upgrade

A. Odczytowe potwierdzenie najnowszego osiągalnego punktu:
Render Dashboard → ai-focus-3-0-db → Recovery → Point-in-Time Recovery.
Sprawdzić wskazane okno i dopuszczalność punktu np. now−30 min, nie uruchamiając recovery.
Dokumentacja wyklucza punkty z ostatnich 10 minut. Jeśli UI nie pokazuje dowodu latest
recoverable timestamp/lag, uzyskać potwierdzenie Render przez oficjalne wsparcie:
„Czy baza dpg-dbh1b0gm7kps73f0p2m0-a na planie 0.1c-256mb ma skutecznie utrwalony
punkt ≤60 min od teraz? Proszę podać najnowszy punkt/lag WAL i rzeczywisty plan/okno
workspace, oraz rozróżnić limit interfejsu 10 min od gwarantowanego opóźnienia.”
Nie wysłano tej wiadomości i nie otwierano okna restore w tej sesji.

B. Po osobnej zgodzie na koszt i operację: jednorazowy PITR do **nowej izolowanej
bazy testowej**, np. do now−30 min. Nigdy nie nadpisywać ani nie przełączać produkcji.
Skopiowana allowlista pozostaje zamknięta; żadnej aplikacji/workerów/Meta na recovery DB.
Nie zmieniać DATABASE_URL istniejącej usługi. Sprawdzić target/time/replay i integralność
READ ONLY, konta/retencję/opt-out; wykonać dowód odzyskania z wymaganym wiekiem punktu.
Nie usuwać instancji automatycznie bez objęcia tego zgodą; zakończenie testu i koszt
trzeba kontrolować. W tej sesji nie utworzono bazy i nie wykonano PITR.

C. Dla ciągłego RPO potrzebny jest nadzór świeżości, nie tylko jednorazowy test.
Proponowane progi do zatwierdzenia: obserwacja co 5 min, warning 30 min, critical 45 min;
przed przekroczeniem 60 min uzgodniony fail-safe/eskalacja. Nie wdrożono monitoringu ani
zatrzymywania zapisów. Bez najnowszego punktu/metryki samo odpytywanie AVAILABLE
nie realizuje takiego monitoringu. Jednorazowy test nie jest gwarancją na wszystkie awarie.

PITR w tym samym providerze nie zastępuje niezależnej kopii przy utracie konta/dostępu
lub dłuższej awarii Render. Nie uzgodniono wyjątku RPO dla tego scenariusza; obecny
stary export/dzienny offsite nie daje niezależnego RPO 60. Zakres wymogu i tę lukę
właściciel powinien rozstrzygnąć przed uznaniem całego recovery za READY.

## Trwała szyfrowana kopia — procedura do osobnej aktywacji

1. Zatwierdzić istniejący magazyn poza ulotnym serwerem aplikacji, region/DPA, koszty,
   retencję i model uprawnień. Propozycja 30 dni jest zgodna z guardem istniejącego kodu,
   ale samo zatwierdzenie RPO nie zatwierdza retencji. Potwierdzić lifecycle i wersje obiektów.
2. Generować klucz/hasło losowo w zatwierdzonym menedżerze sekretów (co najmniej 256 bitów
   entropii), oddzielnie od danych. W kodzie format FOCUS3B1: AES-256-GCM + scrypt,
   losowa sól 16 B, nonce 12 B, AAD focus3-backup. Minimum kodu 20 znaków nie zastępuje
   silnej polityki. Nie generowano ani nie rotowano klucza w tej sesji.
3. Uprawnienia: konto zapisu do wybranego prefiksu, odrębny dostęp odczytu do recovery,
   ograniczony dostęp do klucza i MFA. Klucz nie może istnieć wyłącznie w tej samej
   aplikacji lub bucket. Zapisać niesekretny key/version ID, utrzymać stare wersje do
   wygaśnięcia kopii; nie rotować META_ENCRYPTION_KEY w ramach backupu.
4. Po zgodzie: spójny snapshot z czasem źródłowym, schema revision, manifestem count/SHA,
   następnie szyfrowanie i wysłanie przez TLS. Dopiero potwierdzona trwała kopia z
   poprawnym hashem i odzyskiwalnym kluczem jest punktem recovery, nie start joba.
   Nie zapisywać URL z tokenem, hasła, treści dumpa ani sekretów w logach/repo.
5. Prywatne pliki: katalog 0700, pliki 0600, krótkie życie, usunięcie po kontroli.
   Nie twierdzić, że zwykłe unlink jest certyfikowanym wymazaniem dysku/SSD.
6. Test: pobrać zaszyfrowaną kopię, uwierzytelnić GCM, odtworzyć wyłącznie do nowej pustej
   lokalnej/izolowanej PG17, bez sieci/aplikacji/Meta. Porównać wszystkie 17 tabel,
   count/hash tym samym algorytmem, 004, constraints/indeksy i rejestry usunięć/opt-out.
   Złe hasło/tamper musi zakończyć się przed pg_restore; takie testy są w istniejącej regresji.
7. Niezależnie przetestować odzyskanie klucza przez uprawnionego operatora i ślad dostępu;
   propozycja cyklu testu miesięcznego i po zmianie klucza/formatu wymaga zatwierdzenia.
   Recovery nie może przywracać ważnych starych sesji technicznych/wycofanych zgód.

Nazwy wymaganej przyszłej konfiguracji (bez wartości): BACKUP_PASSPHRASE,
BACKUP_S3_PREFIX_URL, BACKUP_S3_ACCESS_KEY_ID, BACKUP_S3_SECRET_ACCESS_KEY,
BACKUP_S3_REGION, BACKUP_RETENTION_CONFIRMED_DAYS, OFFSITE_BACKUP_ENABLED.
Nie ustawiono żadnej z tych zmiennych.

## Dlaczego obecny offsite nie jest alternatywą RPO 60

scripts/offsite_backup.py działa raz na 86400 s, po błędzie czeka 3600 s. Jest wyłączony.
Backup z scripts/backup.py blokuje tabele w SHARE MODE na czas dumpa i manifestu, co
może blokować zapisy. Nie wolno po prostu włączyć go ani zmienić na godzinowy, aby
zadeklarować RPO 60. Godzinny interwał plus czas backupu/uploadu przekracza budżet,
a awaria wykonania lub wspólna awaria aplikacji jeszcze go wydłuża.

Jeżeli PITR nie zapewni dowodu lub wymagana jest niezależność od Render: osobno
zatwierdzić zewnętrzny scheduler i szyfrowany backup np. co 15 min z budżetem wykonania,
monitoringiem wieku **ostatniego trwałego punktu źródłowego**, retry i alarmami przed
60 min. Harmonogram nie jest dowodem osiągniętego RPO. Najpierw zmierzyć obciążenie,
usunąć niepotrzebne blokowanie zapisów za pomocą spójnego snapshotu i przetestować
awarie. Nie wdrożono takiej zmiany; wymaga kodu, testów i osobnej zgody na infrastrukturę.

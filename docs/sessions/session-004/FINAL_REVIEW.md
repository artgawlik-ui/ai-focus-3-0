# Końcowa kontrola uzupełniająca — 1 listopada 2026

## 1. AGENT_V2_ENABLED=ON — rzeczywista semantyka

**Ta flaga nie jest wyłącznikiem workera ani wszystkich zapisów automatycznych.**
`backend/worker.py:run_once` odbiera zadania queued, odzyskuje zawieszone running,
zmienia statusy queued/running/completed/failed, zapisuje wynik i Activity agent_draft.
Dzieje się to przy ON i OFF; flaga steruje rozszerzoną punktacją/uzasadnieniem.
Pusty queue nie inicjuje samoczynnie wyszukiwania salonów i nie tworzy nowego zadania.
Źródło kolejki: żądanie autoryzowanego użytkownika przez API, a potem automatyczne wykonanie.

`scripts/supervise.py` uruchamia proces workera bez warunku AGENT_V2_ENABLED.
Pętla worker.py odpytuje co 2 s. maintain_meta_once i część maintenance w process_meta_once
uruchamiają retencję również przy Meta OFF. Mogą czyścić treści/metadane oraz zmieniać
stan inboxa zgodnie z polityką; AGENT_V2_ENABLED nie blokuje tych działań.
To również zachowanie kodu produkcyjnego d15265b, zweryfikowane git show, nie nowa aktywacja.
Nie wywoływano żadnej z tych funkcji na produkcji; nie ma dowodu wykonania konkretnych
zadań lub usunięć w działającym procesie. Odczytane zmienne API to konfiguracja, nie dump env procesu.

**Wniosek:** worker może wykonywać automatyczne działania w produkcyjnej bazie, choć
nie wysyła DM i nie tworzy sam wizyt. Jeśli wymagany jest absolutny brak automatycznych
zapisów, obecna flaga tego nie zapewnia. Zmiana konfiguracji/procesów wymaga osobnej zgody;
nie wprowadzono nowej flagi, nie zatrzymano workera i nie zmieniono Render.

DM: transport ma własny fail-closed guard i brak zaimplementowanego HTTP wysyłającego
(nawet true kończy się 501). Płatne AI wymaga odrębnej zgody flagą i klucza;
odczytana flaga AI_PAID_PROCESSING_APPROVED jest OFF. Żadnego realnego wysłania/Graph.
Nowy test `test_agent_flag_is_not_queue_kill_switch_and_never_sends[true/false]` sprawdza
zapis szkicu w obu trybach, brak samoistnego zadania, brak zmiany priorytetu, wizyty i wysyłki;
transport HTTP i send_dm w teście są blokowane. Dane wyłącznie syntetyczne.

## 2. render-readonly.json

Plik dokumentacyjny, dodany jako dowód; nie zmienia runtime ani konfiguracji.
Przegląd ścisłej białej listy kluczy i wartości: service/live/database/sql_read/mutations.
Zawiera publiczny URL, ID zasobów Render, SHA commita, plan/region i statusy.
Nie zawiera rekordów klientów, adresów e-mail, zmiennych poufnych, kluczy, access tokenów,
URL połączenia DB/deploy hook ani treści logów. Nie ujawnia uprawnień dostępowych;
same ID zasobów nie zastępują uwierzytelnienia.
`rg render-readonly.json backend scripts frontend/src migrations render.yaml .github Dockerfile`:
brak odwołań runtime. Wynik walidacji i SHA pliku: render-file-review.json.
Pliki CLI z poświadczeniami są ignorowane przez git; nie dodano ich do commita.
Odczyt metadanych nie uprawnia do stwierdzenia bieżącej integralności danych/flag procesu.

## 3. Dokładne 11 testów wyłączonych

Wykonano tylko collect-only, bez uruchamiania fixture/testów cleanup:
- 1: domyślny ROLLBACK, syntetyczny commit i celowany undo;
- 5: zmieniony salon, dziecko, nowe dziecko, Meta link, aktywny job;
- 1: nieoczekiwany kaskadowy FK;
- 1: niepotwierdzona tożsamość i kolizja przy undo;
- 1: uwierzytelnienie szyfrowanych artefaktów cleanup (FOCUS3C1), w tym AAD/klucz/tamper;
- 1: custom trigger;
- 1: nieznane dzieci FK mimo zatwierdzonego hasha schematu.
To wyłącznie pakiet operatorski usuwania salonu, łącznie z jego kopiami/undo.
Nie jest to 11 testów funkcji CRM/API. Ich wyłączenie dotyczy bieżącego zakazu cleanup;
nie wolno uznać skryptu cleanup za ponownie zweryfikowany lub dopuścić go do produkcji.

Pozostają: test_api (CRM/CRUD/duplikaty/role/sesje/Excel/wizyty/backup permissions),
test_agent_v2/test_qualification, test_meta/test_meta_303/test_meta_304 (OAuth, podpisy,
inbox, refresh, dedup, retencja/opt-out, DM guard), test_meta_migration,
test_synthetic_recovery i test_offsite_backup. Nie wyłączono żadnego z tych przypadków.
Nie mierzono procentowego coverage; nie twierdzimy, że globalna metryka pozostała identyczna.
Zachowano funkcjonalną regresję krytycznych ścieżek aplikacji.

Dodatkowo `test_backup_integrity.py` sprawdza 4 przypadki odrzucenia nieautentycznej kopii
aplikacji (FOCUS3B1): zły klucz, zmieniony szyfrogram, zły AAD i obcięcie. pg_restore jest
zablokowany mockiem, brak sieci/prawdziwego DB i brak użycia kodu cleanup.
Razem z istniejącym pozytywnym restore 17 tabel daje niezależny dowód dla kopii aplikacji,
nie przedstawia wykluczonego testu artefaktów cleanup jako testu wykonanego.

## 4. Status końcowy

READY wyłącznie dowody lokalne/dokumentacja; **BLOCKED dla zgody na wydanie**.
Blokady z REPORT.md pozostają: aktualny SQL/004/konta, świeży trwały backup i restore,
środowisko/artefakt rollback oraz ocena istniejących automatycznych zapisów workera.
Nie zmieniono produkcji. Końcowy commit i checks podane w PR #3; wyniku starego SHA
nie przedstawiać jako wyniku nowego commita. Testy na gałęzi, bez merge/deploy.

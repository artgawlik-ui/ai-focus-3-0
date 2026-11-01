# RAPORT AI FOCUS 3.0.4 — SESJA 001

Data: 2026-11-01. Tryb Autonomicznego Rozwoju V2, wyłącznie lokalny/testowy.

## Cel i stan początkowy

Cel: zamknąć lokalne kryteria etapów 1–2 i przygotować niezależne bramki 3–6.
Rozbieżność zapisana PRZED implementacją w START.md: zamiast f3e739d gałąź miała
6eaed7607b29d4fd579da74ec37b276f2d62aecd; to dodatkowy commit przygotowania cleanup,
nie resetowano historii. PR #3 był otwarty, draft, bez merge. Produkcji nie sprawdzano.
Kryteria zapisano w ACCEPTANCE.md, commit 9893b32.

## Zrealizowane zadania

- Narzędzia diagnostyczne mają lokalny adres domyślny, walidację loopback/portu i odrzucenie
  niejednoznacznych URL przed siecią/odczytem poświadczeń. Historyczne prywatne artefakty
  wymagają odrębnego jawnego opt-in, którego nie ustawiono.
- Guard transportu pytest dodatkowo odrzuca prawdziwe adresy *.onrender.com;
  zachowuje blokadę prawdziwego Meta HTTP. Nie zmieniono flag ani kodu produkcyjnego agenta.
- Nowy test szyfrowanej kopii AES-GCM/scrypt tworzy wyłącznie świeżą bazę syntetyczną,
  odtwarza 17 tabel, porównuje count/SHA-256 z metadanymi i niezmienność źródła,
  usuwa bazę docelową i plik po teście. Klucz testowy losowy, tylko w pamięci procesu.
- Nowy synthetic_export_probe tworzy osobną lokalną bazę, migrację 004 i syntetyczne
  konto/salon; eksport directory, CRC/TOC/SHA, odtworzenie w nowym kontenerze bez sieci.
  Porównano 17 tabel oraz kolumny/PK/FK/indeksy. Kontener, źródłową bazę i pliki usunięto.
- Narzędzie restore przyjmuje opcjonalny, ściśle walidowany syntetyczny prefiks bazy;
  nie zmienia domyślnej zgodności z wcześniejszym formatem eksportu.
- Nowa bramka porównania manifestów odrzuca zmianę count/SHA, brak tabel i błędny manifest;
  dokumentacja opisuje przyszłą kontrolę po redeployu i wyłączenie konta technicznego.
- Nowy preflight Meta działa wyłącznie na przekazanym słowniku konfiguracji testowej;
  zwraca ustawione/puste/zły format, nie wartości, nie czyta produkcji, nie wywołuje API.
- CI otrzymało instalację klienta PostgreSQL 17 do nowego rzeczywistego testu restore.

## Testy i dowody

Dokładne komendy i agregaty: evidence.json; wynik restore: synthetic-restore.json.
Końcowy wynik backendu: 133 passed, 0 failed, 0 errors, 0 skipped (47,18 s); evidence.json.
Frontend: npm run build --prefix frontend, PASS.
E2E: python -m tests.ci_e2e, Chromium desktop PASS, WebKit/iPhone 13 PASS.
To emulacja, nie test na fizycznym iPhonie. Instalację i logowanie na fizycznym iPhonie
wcześniej potwierdził właściciel; nie jest to nowy test tej sesji.
Audyty: pip-audit 32 zależności / zero znanych podatności; npm audit zero podatności.

Pierwszy pomiar bazowy jest NIEWAŻNY: 114 passed, 1 failure, 1 setup error.
Przyczyna: omyłkowe nakładanie dwóch uruchomień na wspólnej syntetycznej bazie, deadlock
oraz kolizja tworzenia tabel. Natychmiast wstrzymano równoległe testy bazodanowe;
powtórka sekwencyjna: 129/129, następna 130/130; końcowy wynik w evidence.json.
Nie było dostępu do produkcji ani ryzyka jej danych. Poprzednie 116 testów z CI jest
historycznym punktem odniesienia; nie przedstawiamy nieudanego pomiaru jako zielonej bazy.
Pierwszy pip-audit nie wystartował z powodu read-only ~/.cache; ponowiono z cache w /tmp.
Dwa ostrzeżenia: przestarzały interfejs pytest zależności i migracja httpx w Starlette;
nie są podatnościami potwierdzonymi audytem, wymagają przyszłej kontroli kompatybilności.

## Status kryteriów

| Etap | Status | Dowód / granica |
|---|---|---|
| 1 | PASS lokalnie | test_salon_cleanup + lokalne guardy; transakcyjny ROLLBACK, celowany undo, zachowane pozostałe dane; produkcyjne usunięcie niewykonane |
| 2 | PASS lokalnie | szyfrowany backup/restore + niezależny bezsieciowy restore directory, 17 tabel, integralność schematu i usunięcie zasobów |
| 3 | READY | pełna regresja/build/Chromium/WebKit i procedury; rzeczywista kontrola po redeployu oraz stan konta technicznego niepotwierdzone i zabronione w tej sesji |
| 4 | READY | przygotowane URI, zakresy, kontrola testowej konfiguracji; ustawienia panelu i aktualność dokumentacji Meta wymagają osobnego potwierdzenia |
| 5 | BLOCKED | implementacja/mocki READY; brak autoryzowanego rzeczywistego testu Development OAuth, nie wykonano wywołań Meta |
| 6 | BLOCKED | trwały inbox/CRM, retry/dedup/retencja sprawdzone lokalnie; brak rzeczywistego dostarczenia Meta Development |
| 7 | BLOCKED — nie rozpoczęty | osobna wyraźna zgoda wymagana, transport DM pozostaje nieuruchomiony |

## Ograniczenia, dane i zgody

Nie wykonano połączeń z produkcyjną bazą, Render ani publiczną aplikacją.
Nie czytano historycznych kopii/archiwów i .render-auth; istniejące archiwa pozostawiono.
Nie wykonano merge, deploy, produkcyjnych migracji/cleanup, zmian flag ani konfiguracji.
Nie wysłano wiadomości ani nie wykonano rzeczywistych wywołań Instagram/Graph API.
Ai Focus 1.0 i 2.0 nie zmieniono: modyfikacje obejmują wyłącznie to repozytorium Focus 3.0;
pełny diff --stat względem main stanowi oddzielny plik diff-main.txt.
Nie deklarujemy gotowości produkcyjnej ani aktualnego stanu jej danych i kont.
Rollback i propozycje operacji zastrzeżonych: OPERATIONS.md; wymagają osobnej zgody.

## Zmiany i commity

Lista plików sesji oraz commity implementacyjne: CHANGES.md i git log.
Raport nie zawiera danych klientów, identyfikatorów produkcyjnych, haseł ani tokenów.

## Szacunek i wznowienie

Pozostaje szacunkowo 5 sesji podstawowych + co najmniej 1 sesja etapu 7.
Licznik zmniejszono tylko o tę sesję z zamkniętymi lokalnymi etapami 1–2;
READY/BLOCKED 3–6 nie potraktowano jako zakończonych operacyjnie.
Nie jest to obietnica czasu; zależy od osobnych autoryzacji i testów rzeczywistych.

Następna sesja: sprawdzić HEAD tej samej gałęzi i status Draft PR #3 w GitHub,
przeczytać niniejsze kryteria i dowody, zachować zakaz dostępu do produkcji.
Zacząć od niezamkniętych kryteriów 3–6, nie powtarzać 1–2 bez zmiany kodu/przyczyny.
Nie używać .render-auth ani historycznych kopii. Testy bazodanowe uruchamiać SEKWENCYJNIE.
Do testów lokalnych: DATABASE_URL=postgresql://postgres@127.0.0.1:55432/focus3_test;
pytest, build, python -m tests.ci_e2e; autoryzację realnego Meta/prod uzyskać osobno.
Nie deklarujemy działania w tle po zakończeniu sesji.

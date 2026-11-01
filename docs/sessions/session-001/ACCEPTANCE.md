# Kryteria zapisane przed rozpoczęciem etapów

## Etap 1 — lokalne oczyszczanie

- E1.1 Testy na nowo utworzonych, jednoznacznie syntetycznych danych PostgreSQL; żadnych danych/ID z produkcji w nowych testach i raportach.
- E1.2 Domyślny SQL kończy się ROLLBACK; testy zakresu, współbieżnych zmian/zależności, zachowania drugiego klienta, kont i sesji oraz celowanego undo są pozytywne.
- E1.3 Dodane lokalne uruchomienia nie mają domyślnego połączenia z Render/produkcyjnym URL. Historyczne skrypty kontroli zdalnej wymagają jawnego opt-in, którego nie używamy.
- E1.4 Stan produkcyjnego oczyszczania: niewykonane; żadnej zgody na wykonanie nie domniemujemy.

## Etap 2 — spójność i odzyskiwanie

- E2.1 Osobna nowa lokalna baza syntetyczna: Alembic 004, pełne 17 tabel, kontrolowane FK i dane źródłowe.
- E2.2 Wygenerowany lokalnie eksport directory ma CRC/TOC/SHA; odtworzenie w nowym kontenerze bez sieci, bez aplikacji i z wszystkimi modułami Meta OFF.
- E2.3 Liczności i fingerprinty wszystkich tabel źródło/odtworzenie zgodne; struktura/indeksy/ograniczenia zgodne; wszystkie utworzone zasoby testowe usunięte.
- E2.4 Zero produkcyjnych danych, API i sekretów. Wynik nie jest testem PITR ani dowodem stanu produkcji.

## Etap 3 — przygotowanie wydania

- E3.1 Pełna regresja backendu, build frontendu i Chromium/WebKit pozytywne; wyniki udokumentowane.
- E3.2 Procedura porównania count/SHA po redeployu zdefiniowana i sprawdzona na danych syntetycznych, z odmową kontynuacji przy różnicy.
- E3.3 Procedura wyłączenia konta technicznego i unieważnienia sesji zdefiniowana i sprawdzona lokalnie; właściciel zachowuje dostęp.
- E3.4 Wykonanie i potwierdzenie kontroli po rzeczywistym redeployu oraz stanu konta technicznego wymaga osobnej autoryzacji. Bez tego etap najwyżej READY, nigdy deklaracja gotowości produkcyjnej.

## Etap 4 — Meta Developers

- E4.1 Udokumentowana ścieżka Unified Login, redirect, minimalne uprawnienia, webhooki i callbacki prywatności oraz wymagania aplikacji/testerów.
- E4.2 Lokalny preflight konfiguracji nie ujawnia wartości ani nie wywołuje API; domyślnie moduły i transport OFF, osobny profil wyłącznie testowy.
- E4.3 Realne ustawienia panelu niezweryfikowane: status najwyżej READY, wymagana czynność właściciela w oficjalnym interfejsie.

## Etap 5 — OAuth

- E5.1 Mocki: właściciel/sesja/state/nonce, jednorazowy kod, błędy, identyfikator konta, scope, szyfrowanie, retry/refresh oraz brak wycieków — pozytywne.
- E5.2 Rzeczywisty Development OAuth na autoryzowanym koncie testowym, bez konta produkcyjnego i bez DM — wymaga dostępnej autoryzacji i osobnego dopuszczenia połączeń. Bez tego etap BLOCKED, kod/mocks READY.

## Etap 6 — inbox/CRM

- E6.1 Lokalny PostgreSQL: podpis przed commitem, trwały inbox, dedup, lease/restart, retry/dead-letter, retencja/usuwanie/rezygnacje, uprawnienia i CRM — pozytywne.
- E6.2 Rzeczywiste dostarczenie z Meta Development do autoryzowanego środowiska testowego — bez niego etap BLOCKED, lokalna część READY. Żadnych odpowiedzi automatycznych.

## Etap 7

Nie rozpoczynać bez odrębnej wyraźnej zgody. Brak implementacji/aktywacji transportu i wysyłki.

## Próby i statusy

Po błędzie: ustalenie przyczyny, poprawka, ponowienie właściwego testu. Po 3 nieudanych próbach ten zakres BLOCKED; niezależne zadania mogą trwać. Incydent, ryzyko utraty lub niepewne pochodzenie danych oznacza stop i raport, nie obchodzenie blokady.

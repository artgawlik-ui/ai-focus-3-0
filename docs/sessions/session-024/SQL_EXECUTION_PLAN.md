# Zgoda A — przygotowanie, bez wykonania produkcyjnego

Status kanału: **BLOCKED**, 9 listopada 2026. Środowisko revision5: observed/current,
network policy enforced, TCP domains=[], ip_ranges=[], VPN=false. Konektor nie oferuje
wewnętrznego Shell; brak narzędzia przeglądarki z zatwierdzonym Shell. **0 SSH,0 SQL**.
Nie testowano ponownie niedostępnego SSH, nie zmieniono sieci ani publicznej allowlisty.

Pakiet pozostaje dokładnie ten sam:
`docs/sessions/session-005/SELECTS.sql` i `scripts/release_selects.py`.
SHA-256 SQL: `795af23ad5acb4d0af451f683e10c9cdfcdcdd10d64bd0f58d6d5b29782815fb`.
Weryfikacja lokalna `SELECTS.sql == render_sql()` PASS; generator ma4 zapytania.
Nie zmieniono żadnego z tych plików. Testy wykonują je tylko na syntetycznym PG17.

## Warunki wykonania po udostępnieniu kanału

1. Istniejąca usługa ai-focus-3-0, baza wskazana w zgodzie A. Zaufana weryfikacja hosta,
   zatwierdzony klucz/autoryzacja, faktycznie dostępny wewnętrzny transport. Sam historyczny
   grant lub dostęp HTTP do panelu nie dowodzi połączenia. Bez accept-new/ssh-keyscan jako
   źródła zaufania, nowych kluczy/ról/tuneli lub publicznej allowlisty.
2. Właściciel prywatnie potwierdza tożsamości owner/technical. Bez zgadywania z nazwy,
   eksportu lub ID w publicznym poleceniu/raporcie. Tych danych tutaj nie potwierdzono.
3. Wewnętrzny DATABASE_URL pozostaje w istniejącym Shell; nie wypisywać go ani env.
   Nie importować aplikacji/workerów, bootstrapu ani starszych narzędzi salon_cleanup.
   Nie przenosić skryptów i nie instalować pakietów w produkcji bez osobnej zgody.
4. Jedna sesja, jedna transakcja REPEATABLE READ READ ONLY, UTC, search_path ograniczony,
   statement_timeout5s, lock_timeout1s, idle timeout10s, na końcu zawsze ROLLBACK.
   Cztery zapytania: baseline → konta → 17 count/SHA → kolejka/inbox/retencja.
5. Baseline musi potwierdzić PG17, rewizję004, dokładnie17 znanych tabel i constraints.
   Rozbieżność/timeout/nieznany obiekt → STOP i ROLLBACK, bez dalszego rozszerzania scope.
   Nie przechodzić na006/007 ani21 tabel w ramach A. Dla takiego schematu potrzebna nowa zgoda.
6. Wynik raportu: booleany, count i SHA zatwierdzonych tabel. Bez treści rekordów,
   identyfikatorów kont, haseł, tokenów i sekretów. Rozbieżności wymagają wyjaśnienia,
   nie automatycznej korekty danych. Snapshot005 nie jest bieżącym baseline produkcji.

## Dlaczego nie użyto konektora SQL

`query_render_postgres` deklaruje READ ONLY, ale każde wywołanie otwiera osobne
połączenie. Nie potwierdza zatwierdzonego wewnętrznego Shell ani wspólnego snapshotu
REPEATABLE READ dla4 zapytań. Aktualna publiczna allowlista bazy jest pusta.
Sama obecność narzędzia nie udziela zgody na alternatywny kanał. Nie wykonano nawet
próbnego SELECT1. Nie wolno otwierać bazy jako obejścia.

Następna czynność właściciela/administratora: udostępnić w oficjalnych ustawieniach
środowiska już zatwierdzony wewnętrzny Shell/SSH istniejącej usługi. Potwierdzić
obsługiwany transport i autoryzację; brak VPN/aktualnych grantów nie znika od samej
wcześniejszej zgody. Nie zmieniać sieci w tej sesji. Potem agent ponownie sprawdzi
stan i hosta; dopiero po prywatnym potwierdzeniu kont wykona wyłącznie pakiet A.

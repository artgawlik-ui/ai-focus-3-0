# Trzy niezależne decyzje — żadna nieudzielona przez sesję 003

## A — Odczyt SQL i weryfikacja kopii

**Cel:** potwierdzić bieżący zakres, konta i możliwość odzyskiwania.
**Warunki:** przypięty kod/checks, zatwierdzony klucz/host/grant, istniejąca usługa i baza,
prywatny katalog narzędziowy, zatwierdzone źródło kopii i izolowane środowisko restore.
**Zakres zgody do osobnego zatwierdzenia:** ograniczony SSH/Shell i transfer narzędzia;
READ ONLY preflight, agregaty i hashe; odczyt metadanych kopii; odczyt/dekryptowanie
zatwierdzonej kopii wyłącznie w bezpiecznej izolacji. Nie obejmuje tworzenia kopii,
zmiany retencji/kluczy, DML, paid PITR ani publicznej allowlisty.
**Kroki:** ACCESS_RUNBOOK → preflight → kontrola trwałego magazynu/klucza → zatwierdzony
restore na kopii → porównanie count/SHA/schematu. Każdy brak lub rozbieżność BLOCKED.
**Ryzyko:** SSH i konto DB mogą mieć szersze uprawnienia; kopia zawiera dane osobowe;
narzędzie ogranicza odczyt, ale nie zastępuje RBAC i bezpiecznego magazynu.
**Rollback:** ROLLBACK/zamknięcie sesji; usunięcie jawnych plików testowego restore po
potwierdzeniu; żadnego przywracania bazy produkcyjnej. Cofnięcie dostępu po zgodzie.

## B — Późniejszy cleanup

**Cel:** usunąć tylko potwierdzone testowe rekordy, bez innych klientów.
**Warunki:** nowy odczyt A, identyczny manifest zakresu (historycznie 13 rekordów),
świeży zaszyfrowany backup i sprawdzony celowany undo, brak aktywnych zależności,
uzgodnione okno i osobne zatwierdzenie aktualnych ID/hash/zakresu poza publicznym logiem.
**Zakres zgody:** dokładny DELETE i COMMIT wyłącznie zatwierdzonego planu;
zgoda A nie wystarcza. Jakakolwiek nowa zależność/rozbieżność wymaga nowej decyzji.
**Kroki:** świeża inspekcja → backup/restore/undo → dry-run ROLLBACK → zatwierdzenie
zakresu → transakcja z guardami → count/SHA pozostałych tabel.
**Ryzyko:** nieaktualna identyfikacja, równoległe zapisy, zależności i niepełny backup.
**Rollback:** przed commit ROLLBACK; po commit wyłącznie zweryfikowany celowany undo
z kontrolą kolizji, bez nadpisywania innych danych; integralność po operacji.
Cleanup nie jest warunkiem technicznym uruchomienia CRM i nie łączy się z deployem.

## C — Późniejszy merge/deploy Meta OFF

**Cel:** opublikować przetestowany 3.0.4 bez uruchamiania Meta.
**Warunki:** aktualne zielone checks dokładnego SHA, A zakończone, świeży zaszyfrowany
backup i test restore, potwierdzony dostępny poprzedni deploy, head 004 i test zgodności,
bezpieczne okno kontroli danych, wszystkie flagi Meta efektywnie OFF.
**Zakres zgody:** merge konkretnego SHA i deploy istniejącej usługi, bez dodatkowych
zasobów/kosztów i bez aktywacji OAuth/webhook/ingest/DM. Nowe migracje wymagają osobnej oceny.
**Kroki:** zapisać SHA/deploy rollback → backup → porównać schemat/flagę każdą osobno
→ merge/deploy po zgodzie → smoke → count/SHA i konta → raport.
**Ryzyko:** przerwa, niezgodność poprzedniej wersji/schematu, naturalne zmiany danych
utrudniające porównanie. Bez kontrolowanego okna nie deklarować pełnej niezmienności.
**Rollback:** poprzedni sprawdzony commit/deploy zgodny z 004, bez DROP ani overwrite DB;
Meta OFF, smoke i ponowna kontrola. Stary backup nie może przywrócić ważnych sesji
technicznych, usuniętych treści lub wycofanych zgód bez zastosowania rejestru zmian.

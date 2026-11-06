# Kryteria 015

- Osobna konfiguracja migracji Google 005, standardowy schemat 004 pozostaje bez zmian.
- OAuth state/session/PKCE, jednorazowy kod, minimalny scope, szyfrowane tokeny i brak sekretów w odpowiedziach/logach.
- Powiązania per użytkownik, zgoda managera, kalendarz dedykowany; brak odczytu cudzych kalendarzy.
- Domyślnie OFF; osobny fail-closed transport zapisów sprawdzany wewnątrz klienta HTTP.
- Trwałe, idempotentne zlecenia synchronizacji: zatwierdzona wersja, ETag, retry, konflikt i anulowanie.
- Disconnect blokuje zlecenia, czyści tokeny, bez usuwania lokalnych/obcych wydarzeń.
- Mocki OAuth/Google i syntetyczny PG; nowe tabele oraz rollback migracji z zachowaniem danych.
- Panel mobilny, pełny CI, PR Draft; bez produkcji/Meta/realnych wydarzeń i kosztów.

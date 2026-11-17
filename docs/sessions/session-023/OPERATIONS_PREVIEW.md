# Podgląd kolejki i retencji dla menedżera

Nowa flaga `FOCUS_DIAGNOSTICS_ENABLED` jest domyślnie OFF. Wyłącznie wartość `true`
(po usunięciu odstępów, bez rozróżniania wielkości liter) udostępnia podgląd.
Brak, pusta wartość, `ON`, `1` lub wartość nieprawidłowa pozostawiają go wyłączonym.
Nie zmieniono produkcyjnych zmiennych ani znaczenia pozostałych flag.

Po osobnym zatwierdzeniu aktywacji: Ustawienia i integracje → Kolejka i retencja Focus
→ Odczytaj stan kolejki. Endpoint `GET /api/focus-calendar/diagnostics` wymaga managera.
Nie zwraca ID kont, klientów, zadań, treści szkiców, wyników analizy ani sekretów.
Odpowiedzi API mają `Cache-Control: no-store`. Brak automatycznego odpytywania panelu.

- Liczniki agenta: queued/running/failed/completed. Wiek najstarszego queued liczony
  od created_at; niepoprawne daty nie blokują podglądu i nie są ujawniane.
- Proces: jedyny bieżący plik statusu, maksymalnie 4096 znaków, walidacja stanu i czasu.
  Sygnał starszy niż 30 s jest nieaktualny; brak, błędny JSON i czas z przyszłości
  dają stan niepotwierdzony. Bez PID i szczegółów pliku. To lokalny sygnał instancji
  API, nie dowód działania wszystkich replik lub sukcesu natywnego cyklu.
- Przypomnienia: tylko aktualni kandydaci z tych samych zapytań co generator, minus
  już aktualnie zapisane dostarczenia. Wykluczenia: opt-out, zakaz kontaktu, nieaktywny
  opiekun, anulowane zadania i niepotwierdzone wizyty. Termin może być przyszły;
  opóźnienie terminu nie jest czasem przebywania w kolejce.
- Schemat native OFF: bez odczytu opcjonalnych tabel. Runtime OFF: metadane mogą być
  odczytane, ale nic nie jest uruchamiane. Błędnie zadeklarowany/niedostępny schemat
  daje kontrolowany komunikat; nie wykonuje automatycznej migracji ani naprawy.
- Podgląd retencji korzysta z istniejącego endpointu, wymaga włączonego modułu native
  i pokazuje propozycję 30 dni dla przeczytanych powiadomień / 365 dni od zakończenia
  zadań do oceny archiwizacji. Nie ma wykonawcy kasowania, nawet przy błędnym ustawieniu
  FOCUS_RETENTION_ENABLED. Nigdy nie usuwa CRM, historii kontaktu ani wizyt.

Nie dodano migracji, połączeń zewnętrznych, procesów, usług ani zależności. Odczyty
są zbiorczymi agregatami SQL; koszt rośnie z liczbą zadań/przypomnień. Nie należy
przedstawiać lokalnych wyników sesji 022 jako SLA panelu na Render.

Wycofanie: wyłączanie flagi wymaga zatwierdzonej zmiany konfiguracji. Cofnięcie kodu
nie wymaga migracji ani odzyskiwania danych, ponieważ podgląd niczego nie zapisuje.
Przed właściwym wydaniem nadal obowiązują RELEASE_GATE, kopia/klucz, RPO, weryfikacja
integralności i kontrolowany handoff. Ta instrukcja nie zatwierdza produkcyjnego wydania.

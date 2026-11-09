# Sesja 022 — kryteria przed implementacją

- HEAD ffeabe0/CI304 i Draft PR3 potwierdzone; zachować ZIP-y i nowsze poprawki.
- Paginacja kontaktów/zadań/wizyt/powiadomień, limity 1–100, stabilny klucz końcowy i RBAC wSQL.
- Filtrowanie salon/handlowiec/data/status/priorytet; agregaty raportów obejmują pełny zakres, nie pierwszą stronę.
- Usunąć N+1 monitoringu; rzeczywiste pomiary i EXPLAIN ANALYZE przy300/1000/5000/10000.
- Kolejne partie przypomnień nie pomijają późniejszych rekordów; test restartu/dwóch workerów/zmian i DST.
- Retencja tylko preview z domyślnymOFF/DRYRUN, bez funkcji kasującej CRM/historię.
- UI z paginacją i filtrami wChromium/WebKit; pełnyCI końcowegoSHA, Draft, bez produkcji.

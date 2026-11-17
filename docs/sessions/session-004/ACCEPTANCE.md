# Sesja 004 — kontrola gotowości wydania, przed testami

1. HEAD/PR/CI odczytane dla dokładnego SHA; żadnego merge/deploy.
2. Kod i migracje: head 004, lokalna migracja/test zgodności bez produkcyjnego DDL.
3. Pełna regresja aplikacji, build, Chromium/WebKit, pip/npm audit. Testy operatorskich skryptów cleanup wyłączone zgodnie z bieżącym zakazem; nie przedstawiać pominięć jako uruchomionych testów.
4. Render tylko READ ONLY: workspace zgodny z wcześniejszym My Workspace, identyfikacja usługi, commit live, autodeploy/health. Odczyt flag bez sekretów; jeśli brak możliwości, BLOCKED.
5. Rollback: bieżący live deploy potwierdzony, aktualne reguły retencji/config z oficjalnej dokumentacji. Nie wykonywać rollbacku ani zakładać dostępności artefaktu z samego statusu live.
6. Rzeczywisty schemat SQL/backup/konta i konfiguracja rozróżnione od dowodów lokalnych. Bez obejścia allowlisty i bez wystawienia endpointów SQL.
7. Raport READY/BLOCKED z dowodami, plikami i ograniczeniami; żadne sekrety lub dane klientów nie trafiają do repo.

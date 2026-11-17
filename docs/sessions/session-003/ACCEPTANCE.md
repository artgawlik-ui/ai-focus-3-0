# Sesja 003 — kryteria przed zmianami

1. HEAD 76330d0 i sukces obu checks tego SHA potwierdzone ponownie; 142 testy przypisane do tego SHA, nie bieżącej produkcji.
2. Runbook Shell/SSH dla istniejącej usługi: zatwierdzony klucz, grant TCP, host key, brak otwierania publicznej allowlisty; dokładne wyjście READ ONLY i warunki STOP.
3. Dry-run lokalny z Meta OFF: jawna kontrola wszystkich flag, schema 004, smoke CRM/autoryzacji, właściciel/techniczne konto; brak wywołań Meta/Render.
4. Recovery i rollback: checklisty świeżej szyfrowanej kopii, retencji i niezależnego klucza, test restore, count/SHA, poprzedni dostępny deploy. Bez twierdzeń o bieżących plikach/deployach.
5. Trzy osobne propozycje zgody: READ ONLY/kopie, cleanup po aktualnym preflight, merge/deploy Meta OFF; cel, kroki, ryzyko, rollback, warunki. Nic nie wykonywane.
6. Plan Meta Development OAuth vs Live webhook, osobne konta/role/uprawnienia i zgody; zero realnych OAuth/Graph/DM.
7. Raport w repo i aktualizacja Draft PR #3 z wynikami i blokadami. Licznik pozostaje 5 podstawowych + ≥1 DM bez zamknięcia operacyjnej bramki.

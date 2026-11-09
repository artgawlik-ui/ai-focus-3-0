# Odrębna macierz dowodów produkcyjnych

| Wymaganie | Istniejący dowód | Brakujący dowód / sposób uzyskania | Status |
|---|---|---|---|
| Integralność bieżącej bazy | Historyczny restore 17/23/004, testy schematu i snapshotów | Dokładnie 4 SELECT-y 005 przez wewnętrzny READ ONLY; prywatne ID, 17 count/SHA i porównanie przed/po wydaniu | BLOCKED: grant TCP pusty |
| RPO ≤60 min | Historyczne PITR AVAILABLE/startsAt, dostępny plan; odtworzony stary dump | Latest skuteczny punkt ≤3600 s + test tej ścieżki recovery i monitoring świeżości; AVAILABLE nie wystarcza | BLOCKED; operacyjny test/ewentualne koszty osobno zatwierdzić |
| Trwały magazyn i klucz | Kod AES-GCM/scrypt/offsite opt-in | Niezależna trwałość magazynu, kontrola dostępu/retencji, odzyskanie klucza bez ujawnienia, test odtworzenia | BLOCKED; nie tworzono kopii/kluczy |
| Rollback Render | Live d15265b w odczycie 012; stare API działa na syntetycznej 004 bez zmiany 17 SHA | Eligibility obrazu, env targetu, osobna zgoda rollback; kod Git nie dowodzi zachowania artefaktu | BLOCKED |
| Handoff workerów | Test rzeczywistych starych/nowych procesów: paused, SIGTERM/kill, resume, jeden szkic | Po zatwierdzonym deployu dowód końca wszystkich starych procesów przed wznowieniem, rozliczenie zmian danych | READY lokalnie / BLOCKED produkcyjnie |

Zgoda A jest udzielona. W 013 odczytano grant raz: domains=[], ip_ranges=[], VPN=false.
Dostępne narzędzia Cloud Environment udostępniają status, ale nie setter reguły TCP;
nie było bezpiecznej operacji umożliwiającej zastosowanie zatwierdzonego grantu.
Nie modyfikowano pliku polityki jako pozornego obejścia. 0 SSH, 0 SELECT.
Najbliższa czynność właściciela: aktywować jedną regułę TCP Codex do
ssh.frankfurt.render.com:22. Bez zmiany publicznej allowlisty PostgreSQL.
Potem host key/autoryzacja i prywatne potwierdzenie ID; nie zakładać ich dostępności.

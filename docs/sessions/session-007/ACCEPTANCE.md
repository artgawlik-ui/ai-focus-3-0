# Sesja 007 — kryteria i zakres przed odświeżeniem recovery

Data: 2026-11-05, Europe/Warsaw. RPO zatwierdzone: 3600 s.

1. Checkpoint 60644d8/RESUME przeczytany; head lokalny/zdalny/PR i checks ponownie potwierdzone, bez resetowania historii.
2. Tylko GET istniejących zasobów: recovery, lista eksportów bez pobierania, plan i live deploy. Nowy timestamp odczytu i wiek ostatniego eksportu; żadnego nowego eksportu/PITR/restore/zasobu.
3. Nie nadawać AVAILABLE znaczenia latest recoverable point. Jeśli brak dowodu ≤3600 s, RPO pozostaje BLOCKED.
4. Oddzielić brak zgody A od przeszkody sieciowej SQL; nie uruchamiać produkcyjnego SQL bez A ani nie otwierać allowlisty. Nie uruchamiać historycznych skryptów .tools.
5. Nie powtarzać ukończonego restore tego samego SHA ani lokalnych testów niezmienionej aplikacji. Raport z nowymi dowodami i jednym minimalnym następnym krokiem właściciela.
6. Raport/session checkpoint w tej samej gałęzi i Draft PR, bez merge/deploy/produkcji/Meta. Licznik bez zmniejszania za niezamkniętą bramkę operacyjną.

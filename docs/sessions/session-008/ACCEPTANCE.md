# Sesja 008 — kryteria przed implementacją

1. HEAD/PR/CI checkpointu zgodne; nowe zmiany zachowane.
2. Sprawdzenie grantów bez prób SSH przy pustej polityce; SQL tylko po potwierdzeniu kanału.
3. Supervisor zamyka już uruchomione dzieci również po błędzie startu kolejnego procesu.
4. Testy supervisora wyłącznie na mockach: błąd startu, awaria dziecka, SIGTERM i przekroczenie czasu zamykania; brak bazy, sieci i prawdziwych procesów potomnych.
5. Zachowane polecenia API/workera, domyślne flagi i limit zamykania 25 s.
6. Raport i RESUME zawierają aktualne zgody A/kontrolowany worker oraz otwarte RPO.
7. Zapis na gałęzi roboczej; PR Draft, bez merge/deploy/produkcji. Wynik CI przypisany do SHA.

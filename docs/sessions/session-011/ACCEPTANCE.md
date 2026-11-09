# Kryteria 011

- Stary wykonawca nie zapisze szkicu ani błędu po ponownym przejęciu zadania.
- SIGTERM nie rozpoczyna kolejnego etapu cyklu; pauza nie uruchamia retencji/CRM/Meta.
- Diagnostyka procesu bez danych klientów i sekretów; API health nie jest health workera.
- Testy PG17: odzyskanie running, równoległy stary/nowy worker, pojedynczy szkic.
- Plan pierwszego rollout uwzględnia stare procesy bez nowych zabezpieczeń.
- Brak migracji i operacji produkcyjnych; CI końcowego SHA success przed PASS.

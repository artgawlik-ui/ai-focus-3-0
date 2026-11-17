# Kryteria sesji 010

- Worker finalizuje szkic i opt-out/powiązanie rozmowy używając tej samej blokady transakcyjnej salonu.
- Brak blokady w czasie HTTP modelu; brak migracji; zwolnienie blokady przez commit/rollback.
- Testy syntetycznego PostgreSQL sprawdzają oba porządki transakcji i zmianę przypisania rozmowy.
- Regresja workera i CRM, końcowy CI success przed PASS.
- Bez produkcyjnego SQL, konfiguracji, kosztów, Meta/DM, merge/deploy.

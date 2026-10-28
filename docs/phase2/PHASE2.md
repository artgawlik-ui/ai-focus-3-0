# Faza 2 — kandydat wydania 3.0.1

Rozwinięto istniejący CRM. Nie zmieniono schematu PostgreSQL ani istniejących rekordów. Włącznik AGENT_V2_ENABLED steruje rozszerzoną punktacją; AI_PAID_PROCESSING_APPROVED=false i OFFSITE_BACKUP_ENABLED=false utrzymują nowe koszty wyłączone.

Implementacja: backend/qualification.py, backend/worker.py, backend/main.py, backend/schemas.py, frontend/src/main.tsx, render.yaml. Testy: tests/test_qualification.py, tests/test_agent_v2.py, tests/test_api.py, tests/test_offsite_backup.py, tests/ci_e2e.py, tests/production_browser_check.py. Dokumentacja: docs/phase2/AI.md, PHASE2.md oraz końcowy REPORT.md.

Zakres: jawna punktacja z uzasadnieniami i źródłami, bez wymyślania braków, szkice zależne od specjalizacji CRM, wstępne etykiety odpowiedzi do ręcznego przeglądu, rekomendacje kolejnego kroku i sprawdzenia dostępności przed wizytą. Wyniki pozostają w trwałej kolejce/historii i są widoczne w mobilnym panelu agenta. Model zewnętrzny opcjonalnie proponuje neutralne pytania, nie zmienia punktacji ani CRM; test transportu jest syntetyczny. Poprawiono odcięcie dostępu starego opiekuna do zadań i wizyt po zmianie przypisania, a worker ponownie sprawdza uprawnienia przed analizą. Zmiana hasła odrzuca banalne hasła i ogranicza błędne próby starego hasła.

`DATABASE_URL=<izolowana focus3_test> python -m pytest -q`: 29 passed, 2 ostrzeżenia deprecacji. `npm run build --prefix frontend`: PASS. Rozszerzone E2E obejmują zadanie agenta, priorytet i źródła w obu silnikach. Końcowe wyniki CI i wdrożenia są w REPORT.md; sam ten plik nie stanowi potwierdzenia wdrożenia.

Brak realnego wywołania płatnego modelu, wysyłki wiadomości i tworzenia wizyt klientom. Fazy 3–6 nie rozpoczęte. Focus 1.0 i 2.0 bez zmian. Ograniczenia reguł, koszt hipotetycznego modelu i zasady przetwarzania: AI.md. Backup offsite pozostaje przygotowany do konfiguracji magazynu, a nie aktywny.

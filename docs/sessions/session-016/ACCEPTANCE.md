# Kryteria sesji 016

- Potwierdzić HEAD/PR/CI oraz status konfiguracji Google bez wartości sekretów.
- Oddzielić potwierdzone wymagania Web OAuth/PKCE/app.created od testu live (brak klienta = BLOCKED).
- Odtworzyć restart/timeout po udanym PATCH przed commitem; wznowienie ma potwierdzić ten sam stan bez kolejnego zapisu.
- Zmiana zdalna niezgodna z zatwierdzonym payloadem nadal wymaga przeglądu (ETag).
- Zachować RBAC, state/session/PKCE, replay, szyfrowanie i domyślne OFF.
- Przetestować 004->005, ponowny upgrade i marker rollback bez zmiany danych CRM/Google.
- Lokalny PG/mocked HTTP; pełne CI końcowego SHA, Draft, bez produkcji/realnych wydarzeń.

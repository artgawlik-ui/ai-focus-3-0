# Krok 0 — rozpoznanie i plan 3.0.3

Punkt bazowy main: ba951fd43a0ef5d81e61457f7a541300e9b3b336.
Audyt źródłowy skopiowany za zgodą właściciela do AUDYT-BAZOWY.md.
Bazowe `DATABASE_URL=<lokalna baza testowa> .venv/bin/python -m pytest -q --tb=no --show-capture=no`: 49 passed, 0 failed, 0 skipped (JUnit /tmp/3.0.3-baseline.xml). Pierwsza próba przy zatrzymanym lokalnym PostgreSQL: 10 passed, 39 errors; po uruchomieniu istniejącego kontenera wynik powyżej.

## Inwentarz i przepływ przed zmianą

- META_ENABLED: backend/meta.py enabled/require_config, status, agent_replies, worker maintenance i backend/main.py integrations; domyślnie false. Włącza wspólnie OAuth, weryfikację/odbiór webhooków, historię, diagnostykę i subskrypcję. Nie istnieje transport DM.
- META_MODE: require_config, wymagane development; brak wartości blokuje integrację. Jest strażnikiem trybu, nie flagą wysyłki.
- Innych flag Meta/Instagram w aktualnym kodzie brak. META_APP_ID, APP_SECRET, CONFIG_ID, VERIFY_TOKEN, ENCRYPTION_KEY, TEST_ACCOUNT_ID, REDIRECT_URI są konfiguracją, nie flagami.
- OAuth: właściciel + CSRF -> state/nonce przypisane do sesji -> jednorazowy callback -> wymiana kodu GET -> debug_token -> assigned_instagram_accounts -> Fernet w PostgreSQL. Nazwa docelowa była odrzucana mimo prawidłowego ID.
- Webhook: podpis -> synchroniczne przetwarzanie CRM z blokadą credential -> commit -> 200. Deduplikacja dopiero w meta_messages; brak trwałego inboxa.
- /refresh i maintenance: debug_token; dotychczas błędy mogły usuwać poprawny token, a maintenance trzymało blokadę podczas HTTP.
- Diagnostyka /status, ręczne szkice/akceptacja/oświadczenie manual_sent. Brak metody /send i transportu DM.

## Plan i pliki

1. backend/meta_flags.py: jawne niezależne flagi, zgodność konfiguracji legacy, blokada transportu wewnątrz funkcji.
2. backend/meta.py: rozdzielenie bramek, usunięcie blokady nazwy, bezpieczny callback/logi; delegacja inboxa i sprawdzania tokenu.
3. backend/meta_models.py, migrations/versions/004_meta_durable_inbox.py: dwie addytywne tabele, indeksy; rollback bez kasowania danych.
4. backend/meta_inbox.py i backend/meta_refresh.py: trwały odbiór, dzierżawy, SKIP LOCKED, retry, retencja, diagnostyka; HTTP poza transakcją blokującą.
5. backend/worker.py, backend/db.py: istniejący cykl agenta, ograniczona pula PostgreSQL, bez nowej usługi/wątku.
6. tests/test_meta.py, nowe testy regresyjne/współbieżności/migracji; dokumentacja i raport.

## Decyzje

Zatwierdzone przez właściciela: payload zakończonego inboxa 7 dni; metadane 90 dni; alert pending >=100, najstarszy pending >300 s lub dowolny dead-letter; cykl w istniejącym procesie agenta. Brak nowego wątku, procesu, usługi i kosztu.
Proponowane limity techniczne: batch 4, lease 120 s, 5 prób z backoff 5–300 s, payload 64 KiB, maks. 50 zdarzeń/request, pula 2 połączenia/proces bez overflow. Próg ostrzeżeń failed pokazany oddzielnie.
Retencja 7/90 dotyczy wyłącznie zakończonych zdarzeń; failed/dead-letter wymagają interwencji właściciela i nie są automatycznie usuwane. Ryzyko wzrostu inboxa będzie opisane.

## Migracja konfiguracji (bez wykonywania na produkcji)

META_ENABLED zachowuje funkcję domyślnej bramki legacy. Nieobecne nowe flagi dziedziczą jej wynik. Jawna nowa flaga steruje wyłącznie swoim modułem (opcja nowej konfiguracji). Puste/niepoprawne nowe flagi = false. Profil odbiorczy wymaga świadomego ustawienia flag modułów; nie zmienia się żadna wartość w Render.
META_DM_TRANSPORT_ENABLED nie dziedziczy żadnej flagi, brak/puste/niepoprawne=false; nawet true nie dodaje implementacji wysyłki. W tej poprawce transport pozostaje niedostępny.

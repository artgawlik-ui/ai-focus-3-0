# Ai Focus 3.0 — fazy 1–2, raport końcowy 2026-10-28

**CRM i nowy silnik rekomendacji wdrożone i zweryfikowane. Fazy 3–6 nie zostały rozpoczęte. Automatyczne kopie offsite są przygotowane, lecz nieaktywne; pełna gotowość operacyjna nie jest deklarowana.**

Aplikacja: https://ai-focus-3-0.onrender.com . Wersja API 3.0.1, faktycznie uruchomiony commit **df78fd7802c7e93d007b92ab0093ba7d33df8fee**. Render: `dep-dbh643d09sns738hqbe0`, live od 21:00:07 UTC. Punkt powrotu: `0c44401d2b8ef2b7d11813e35aed69ab3b0de6fe` / `dep-dbh4jsd9el5s73ap7n50`. Rollback nie był konieczny ani ćwiczony. Aktualizacja konfiguracji wywołała wdrożenie; drugie zbędne wdrożenie tego samego commita anulowano przed publikacją. Nie było nowej aplikacji ani bazy.

## Warunki startowe i hasło

Przed pracą Render potwierdził oczekiwany live commit 0c44401, zamknięty audyt zależności oraz nieaktywne konto techniczne. Świeża zaszyfrowana kopia przed planowaną zmianą hasła została pobrana i odtworzona do pustej lokalnej bazy, zgodność wszystkich 10 tabel. Osobną świeżą kopię wykonano bezpośrednio przed wdrożeniem; zachowano wcześniejszą kopię. Obie pozostają prywatne, poza Git i raportem.

Właściciel **samodzielnie potwierdził instalację PWA na fizycznym iPhonie i logowanie do swojego konta**. To potwierdzenie właściciela, nie test fizycznego urządzenia wykonany przez Codex. Hasła nie zmieniano ani nie ujawniano. Właściciel zmienia je w aplikacji: Ustawienia i integracje → Bezpieczeństwo konta, podając stare hasło. Argon2id, minimum 12 znaków, odrzucanie wybranych banalnych haseł, blokada po 8 błędnych próbach logowania/15 min oraz osobna blokada po 8 błędnych próbach obecnego hasła. Zmiana unieważnia pozostałe sesje. Zalecana unikalna fraza 16+ znaków. MFA nie jest jeszcze dostępne w CRM.

## Faza 1 — działa / przygotowane

**Działa:** dotychczasowy CRM, role i przypisania, historia mutacji; nowe logi dostępu API z kontem, szablonem trasy, czasem i wynikiem, bez body, sekretów i parametrów wyszukiwania. Produkcyjna próbka logów Render zawiera 3 nowe wpisy audytowe. Logi platformy nie są niezmiennym, niezależnym archiwum audytu.

**Przygotowane:** codzienny szyfrowany backup pg_dump/AES-GCM do prywatnego S3 przez HTTPS i Signature V4, uruchamiany jako opcjonalny proces istniejącej usługi. Bez dodatkowego Render cron. Test uploadu wykorzystuje syntetyczne zaszyfrowane bajty i atrapę transportu, sprawdza brak przekierowań i usunięcie pliku tymczasowego. Nie przeprowadzono rzeczywistego uploadu, weryfikacji lifecycle ani alertów zewnętrznych. OFFSITE_BACKUP_ENABLED=false. Zdalny magazyn i jego koszt wymagają decyzji właściciela, bez przekazywania sekretów w rozmowie; szczegóły bezpiecznej konfiguracji: [BACKUPS.md](BACKUPS.md).

[PRIVACY.md](PRIVACY.md) opisuje źródła/daty danych, minimalizację, wymagane podstawy prawne komunikacji handlowej i przetwarzania, sprzeciw/do_not_contact, obsługę praw osób oraz proponowaną retencję. Automatyczne usuwanie danych i pełny rejestr zgód nie są wdrożone. Dokumentacja wspiera administratora danych, nie zastępuje jego oceny prawnej i polityk.

## Faza 2 — faktycznie działa

- Punktacja 0–100, sugestie A+/A/B/C i jawne kryteria oparte na zapisach CRM: specjalizacja, deklarowany potencjał, etap lejka i region Głogowa. Każde kryterium ma źródło; wynik ma wersję reguł, datę, wykaz braków i źródła. Braki to „brak informacji”, nie domysły. To heurystyka do walidacji, nie prognoza rzeczywistych zakupów.
- Szkice korzystające ze specjalizacji CRM, historia kontaktów i rekomendacja odczekania po niedawnym kontakcie. Swobodna treść operatora jest niezweryfikowana i nie podnosi punktacji.
- Wstępne etykiety ręcznie zapisanych odpowiedzi: możliwa rezygnacja, możliwe zainteresowanie wizytą, przegląd ręczny. Potencjalna rezygnacja blokuje szkic. Proste reguły mogą się mylić; nie ma aktywnego monitorowania skrzynki ani Instagrama.
- Rekomendacja sprawdzenia dostępności przed wizytą; żadnego samodzielnego rezerwowania. Wynik i źródła w trwałym zadaniu, wpis w historii relacji, priorytet/uzasadnienia/źródła w mobilnym panelu agenta. Każda wiadomość i wizyta wymagają zatwierdzenia właściciela. Brak endpointu wysyłki; sent=false.
- Naprawa kontroli dostępu po zmianie opiekuna: poprzedni handlowiec traci dostęp do zadań i wizyt salonu, worker ponownie sprawdza aktywność i przypisanie przed analizą. Agent nie zmienia automatycznie priorytetu ani lejka CRM.

AGENT_V2_ENABLED=true; rozszerzoną punktację można wyłączyć. W razie regresji pełny powrót kodu do punktu 0c44401, bez migracji wstecz. Fazy 1–2 nie dodają ani nie zmieniają schematu.

## Testy i bezpieczeństwo

| Kontrola | Dowód / komenda | Wynik |
|---|---|---|
| Faza 1 | `pytest -q tests/test_api.py tests/test_offsite_backup.py` na izolowanej focus3_test | 20 passed w punkcie fazy 1 |
| Pełna regresja fazy 2 | `pytest -q --junitxml=test-results/phase2-tests.xml` na izolowanej PostgreSQL | **29 passed** |
| Frontend | `npm run build --prefix frontend` | PASS, TypeScript/Vite |
| E2E | `python -m tests.ci_e2e` | Chromium + WebKit/iPhone 13 PASS, dane syntetyczne |
| Restart | `AGENT_V2_ENABLED=true python -m tests.system_check` | PASS, dane i wynik przetrwały restart API/workera |
| Audyty | `pip-audit -r requirements.txt`; `npm audit --prefix frontend` | **0 znanych podatności**, powtórzone przed wdrożeniem |
| Skan zmian | phase2-secret-scan.json | 30 zmienionych plików względem starego wydania, 0 dopasowań sprawdzanych wzorców sekretów |
| Produkcyjne HTTPS/UI | phase2-production-ui.json | Chromium + WebKit PASS, 0 mutacji, 0 błędów JavaScript |
| Dane i gotowość | phase2-production-readonly-audit.json | 10 tabel zgodnych, health 200, wersja 3.0.1, anonimowy CRM 401 |

[Pełne CI gałęzi, przed wdrożeniem: SUCCESS](https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/40767508671). [CI main tego samego commita: SUCCESS](https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/40768004448). Zależności nie zmieniły wersji w tym etapie. Dwa ostrzeżenia deprecacji bibliotek testowych nie powodują błędów; wymagają przyszłej aktualizacji narzędzi testowych. Skan wzorców nie dowodzi braku każdego możliwego sekretu.

E2E obejmują dotychczasowy login/logout, formularz CRM, sesję, PWA/offline/cache oraz nowe zlecenie agenta, wyświetlenie priorytetu i źródeł. WebKit offline sprawdzano przez kontrolowane zerwanie sieci lokalnego proxy, nie przełącznik trybu samolotowego fizycznego iPhone'a. Produkcyjne odczyty przeprowadzono z aktywną weryfikacją TLS po skonfigurowaniu zaufania do CA proxy środowiska testowego.

## Integralność i kopie

Baza pozostaje `ai-focus-3-0-db`, `dpg-dbh1b0gm7kps73f0p2m0-a`, available, plan 0.1c-256mb; zewnętrzna allowlista pusta. Liczebności i SHA-256 wszystkich **10 tabel zgodne przed/po wdrożeniu i po końcowym odczycie UI**: activities 6, alembic_version 1, appointments 1, integration_links 0, jobs 1, login_attempts 0, salons 1, sessions 2, trainings 0, users 2. Skróty: [evidence/integrity-baseline.json](evidence/integrity-baseline.json). Konto właściciela aktywne, jego sesja przetrwała wdrożenie, techniczne nieaktywne. Liczba sesji została utrwalona w nowym punkcie odniesienia — nie porównywano jej ze starszą sesją sprzed logowania właściciela na iPhonie.

Nie dodano klientów demo ani rzeczywistych testowych wiadomości/wizyt na produkcji. Zachowano wcześniejszy, oznaczony rekord techniczny; nie usuwano danych. Deklarowane 118 salonów nadal nie zostało zweryfikowane ani zmigrowane.

Świeże kopie odtworzono tylko do lokalnych pustych baz i usunięto wyłącznie te tymczasowe bazy. `alembic upgrade head` na odtworzonej kopii nie zmienił jej integralności. Kopii nie odtwarzano na produkcji. Render PITR pozostaje mechanizmem platformy; nie uruchamiano jego natywnego odtworzenia do dodatkowej płatnej instancji. Procedura odzyskiwania: [../RECOVERY.md](../RECOVERY.md). Automatyczny offsite, retencja magazynu, alerty i cykliczne realne testy odtwarzania pozostają otwartym zadaniem operacyjnym.

## AI, integracje, koszty i następne decyzje

Silnik lokalny działa, OpenAI jest **nieaktywne**: AI_PAID_PROCESSING_APPROVED=false. Adapter i test transportu przygotowane. Minimalny kontekst nie zawiera nazw, danych kontaktowych, historii ani swobodnego tekstu. Szczegóły przetwarzania/DPA/retencji i źródła cennika: [AI.md](AI.md). Szacunek dla gpt-4.1-mini: ok. 0,64 USD / 1000 analiz po 400 tokenów wejścia i 300 wyjścia, przed podatkami. To nie jest uruchomiony koszt ani zaakceptowany limit. Nie wykonano płatnego wywołania.

Koszt bazowy Render pozostaje około 13 USD/mies. plus podatki/zużycie ponad limity; **nowe płatne zasoby: 0**. Koszt magazynu kopii zależy od dostawcy i wymaga osobnej akceptacji. Przed aktywacją: właściciel wybiera prywatny magazyn/region/retencję i budżet AI, następnie konfiguracja sekretów wyłącznie przez oficjalne panele. Niczego nie trzeba przesyłać w rozmowie.

Meta/Instagram, Google Calendar OAuth, Livespace i dalszy moduł zespołowy nie były realizowane w tym uruchomieniu — fazy 3–6 wymagają kolejnej zgody. Dotychczasowy ręczny link Calendar i CRM zachowane. Automatyczna wysyłka wyłączona. Brak MFA i kompletnej automatyzacji retencji/DSR pozostają ograniczeniami.

## Pliki i niezależność

Zmiany funkcjonalne faz 1–2: backend/main.py, backend/security.py, backend/schemas.py, backend/qualification.py, backend/worker.py, scripts/offsite_backup.py, scripts/supervise.py, frontend/src/main.tsx, render.yaml; testy: tests/test_api.py, tests/test_offsite_backup.py, tests/test_agent_v2.py, tests/test_qualification.py, tests/ci_e2e.py, tests/production_browser_check.py; dokumentacja: docs/phase2/*.md, evidence/* oraz aktualizacje README/statusów.

Commity faz: `40ea76c7eeda79d22059a48c92c07e8589d5686b` (faza 1), `df78fd7802c7e93d007b92ab0093ba7d33df8fee` (faza 2). Późniejszy commit raportu nie oznacza kolejnego wdrożenia aplikacji.

**Focus 1.0 i Focus 2.0: bez zmian w kodzie, usługach, konfiguracji i danych.** Nie wysłano żadnych rzeczywistych wiadomości klientom i nie utworzono rzeczywistych spotkań. Zakończono ten zakres prac; fazy 3–6 zatrzymane.

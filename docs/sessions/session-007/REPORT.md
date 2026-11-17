# RAPORT AI FOCUS 3.0.4 — SESJA 007

Data: 5 listopada 2026, Europe/Warsaw. **Status wydania: BLOCKED.**
Wykonano dozwolone wznowienie i świeże kontrole metadata; nie powtarzano zakończonych etapów.

## Punkt startowy

RESUME.md odczytano z GitHub przed rozpoczęciem pracy. Lokalny HEAD, zdalna gałąź i PR
zgodne: 60644d8bc208f356060b7629273c1412786d14a2, PR #3 open/Draft/bez merge,
baza PR d15265b26524d594bdbcb4bc6b63fcbc398a1424. Obie kontrole tego SHA odczytane PASS:
- https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/41362554862
- https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/41362548637
Nie znaleziono AGENTS.md w repozytorium. Zachowano 3 nieśledzone archiwa; nie otwierano ich.
Środowisko zgłosiło running/connected i aktualne obserwacje. Polityka: unrestricted HTTP,
TCP domains/ip_ranges puste, VPN=false. Nie zmieniano środowiska.

## Co rzeczywiście odświeżono

Tylko GET API/MCP, w zweryfikowanym wcześniej My Workspace. Oficjalny Render CLI
uwierzytelniony bez ponownego loginu; sekret użyty tylko do uwierzytelnienia API,
bez zapisania w dowodach/logach. Nie używano cookies aplikacji ani historycznych sesji CRM.

Recovery/lista eksportów/deploy: 2026-11-05 **16:04:18–16:04:20 UTC / 17:04:18–17:04:20 Warszawa**.
Osobny odczyt flag wykonano później tego samego dnia; znacznik zapisu dowodu w configuration-readonly.json.
- PostgreSQL available, major 17, plan 0.1c-256mb, publiczna allowlista pusta.
- Usługa ai-focus-3-0, main, autodeploy no; live nadal
  **d15265b / dep-dbjhl6jbc2fs73crj65g**. 3.0.4 nie jest wdrożone.
- Recovery AVAILABLE, **startsAt=2026-11-01T06:32:50Z**. Dolna granica zmieniła się
  względem sesji 006, ale API nadal zwraca tylko recoveryStatus/startsAt.
  Brak endsAt, latest recoverable timestamp i lag WAL — nie potwierdzono RPO 60.
- Nadal 3 eksporty z 1 listopada; najnowszy z **18:25 UTC / 19:25 Warszawa**,
  wiek **337161 s = 93 godz. 39 min 21 s**, znacznie ponad 3600 s.
  To stan listy API, nie ponowne sprawdzenie pobrania pliku. Nie pobierano ani nie
  odtwarzano eksportu. Według niezmienionej dokumentacji eksporty są przechowywane
  7 dni; nie opierać trwałego zabezpieczenia danych wyłącznie na tej czasowej liście.
- Zapisane flagi Meta/OAuth/webhook/ingest/DM efektywnie OFF, env groups 0.
  AGENT_V2 nadal ON, paid AI i offsite OFF. To zapisane ustawienia API, nie zrzut env procesu.
  Worker i retencja nie zostały zatrzymane; żadnej ich funkcji nie uruchamiano ręcznie.

Oficjalne postgresql-backups.md: HTTP 200, SHA identyczny z sesją 006. Dokument nadal
określa okno Hobby 3 / Pro+ 7 dni, wyklucza ostatnie 10 minut wyboru i przechowuje eksporty
7 dni. Nie reinterpretowano tego jako SLA RPO ani dowodu skutecznego PITR.
Dokumentacja i odczyty: provider-readonly.json, configuration-readonly.json,
documentation-readonly.json. Do plików nie trafiły podpisane URL ani dane klientów.

## Co celowo nie zostało powtórzone

Nie uruchamiano lokalnie pełnej regresji/build/E2E/restore, bo aplikacja i zależności
nie zmieniły się od checkpointu. Historyczne 143 testy/Chromium/WebKit/audyty są
przypisane do tamtych SHA, nie nowemu commitowi raportu. Standardowy CI nowego SHA
może uruchomić syntetyczne testy po push; końcowy wynik sprawdzić w Checks PR #3.
11 testów operatorskiego cleanup nadal wyłączonych, brak pomiaru procentowego coverage.
Nie pobierano dawnych prywatnych dumpów, nie odtwarzano ponownie znanego snapshotu
17 tabel/23 rekordów/004. Ten dowód pozostaje ważny wyłącznie dla tego snapshotu.

## Stan blokad

| Zakres | Wynik |
|---|---|
| Wznowienie gałęzi i odczyt bazowego CI | PASS |
| Aktualne metadata Render/PITR/lista eksportów | PASS READ ONLY |
| Kod/restore snapshotu z wcześniejszych sesji | Zachowane dowody; brak potrzeby powtórki |
| RPO 60 | BLOCKED — brak latest point/testu PITR; eksport za stary |
| Zgoda A na SQL | BLOCKED — nieudzielona |
| Kanał SQL | BLOCKED — brak wewnętrznego kanału/grantu, pusta allowlista |
| Aktualne 004/konta/sesje/hash danych | Niepotwierdzone bez SQL |
| Trwała szyfrowana kopia/klucz/retencja | Niepotwierdzone |
| Artefakt/env rollbacku i tryb zapisów workera | Nadal do zatwierdzonej kontroli |
| PITR testowa DB/nowe koszty/merge/deploy/Meta | Niezatwierdzone; niewykonane |

Nie ma podstaw do READY ani do zmniejszenia licznika: **5 sesji podstawowych + ≥1 DM**.
Nie rozpoczęto etapu komunikacji wychodzącej. AVAILABLE nie zamyka RPO, a zielone
CI nie zastępuje produkcyjnych odczytów i zgód.

## Jeden następny krok właściciela

**Zatwierdzić zgodę A na dokładny minimalny SELECT-only preflight** opisany w
AUTHORIZATION_REQUEST.md. To oddzielne od zapewnienia działającego wewnętrznego
kanału Shell/SSH i ograniczonego grantu. Nie prosimy o hasło, token, MFA ani klucz.
Dostęp API działa; ponowne logowanie Render nie rozwiąże blokady SQL.

Po A i udostępnieniu kanału agent może wykonać odczyty samodzielnie. Bez obu warunków
nie powielać kolejnych sesji z tymi samymi lokalnymi testami, planami i restore.
Odrębne zgody na koszt/test PITR, nowy eksport, sieć/sekrety, cleanup i merge/deploy
nie wynikają z A. Nie wysyłano wiadomości do wsparcia Render.

## Zapis, bezpieczeństwo i wznowienie

b9c2e21: kryteria wznowienia przed kontrolą recovery. Kolejny commit zawiera raport,
metadata, prośbę A oraz aktualizację RESUME.md; SHA w git log i PR #3.
Zmiany wyłącznie dokumentacyjne w tej samej gałęzi. Brak zmian aplikacji/migracji,
produkcyjnych danych/konfiguracji/sekretów/sieci, eksportów, restore/PITR, restartów,
merge/deploy, paid resources i Meta/DM. Focus 1.0/2.0 nietknięte.

Wznowić od RESUME i aktualnych zgód/warunków. Priorytetem jest A i dostęp SQL,
nie nowy kod lub powtarzanie testów zakończonych etapów. Nie działamy w tle po sesji.

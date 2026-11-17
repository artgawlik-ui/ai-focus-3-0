# Procedury V2 — wyłącznie propozycje operacji zastrzeżonych

## Etap 1: oczyszczenie

Cel: usunąć jednoznacznie zatwierdzone dane testowe bez zmiany innych klientów.
Kod: scripts/salon_cleanup.py, scripts/cleanup_backup.py; SQL domyślnie kończy się ROLLBACK.
Warunki: osobna pisemna zgoda na dostęp do produkcji, identyfikacja rekordów i relacji,
świeży zaszyfrowany backup oraz zakończony test jego odtworzenia. Historyczny eksport nie
potwierdza aktualnego stanu. W tej sesji nie używano żadnego eksportu produkcyjnego.
Kroki przyszłe: inspekcja tylko po zgodzie -> zatwierdzenie zakresu -> backup -> dry-run
-> osobne zatwierdzenie wykonania -> kontrola zachowanych tabel.
Ryzyko: błędna identyfikacja lub równoległa zmiana; skrypt odrzuca zmienione hashe,
nieznane relacje/triggery oraz aktywne zadania. Rollback: ROLLBACK przed commit;
po zatwierdzonym commit wyłącznie sprawdzony celowany undo z szyfrowanej kopii.

## Etap 3: bramka wdrożenia i kontrola po redeployu

Nie wykonywać w tej sesji. Wymagana osobna zgoda na Render i produkcyjną bazę.
Przed operacją: zapisać działający commit/deploy, świeży szyfrowany backup, test restore,
sprawdzić migracje na kopii i komplet backend/build/Chromium/WebKit/audytów.
Na czas porównania zatrzymać zapisy po osobnym uzgodnieniu okna z właścicielem.
Zapisać fingerprint(url, include_metadata=True) w bezpiecznym miejscu poza repo;
po wdrożeniu ponownie obliczyć w transakcji READ ONLY i przez scripts/data_release_gate.py porównać dokładnie nazwy tabel,
liczby i SHA-256. Jakakolwiek różnica blokuje odbiór, wymaga wyjaśnienia; nie nadpisywać danych.
Przy zatwierdzonej migracji porównanie musi uwzględniać jawnie uzasadnione różnice schematu.
Brak okna bez zapisów oznacza brak wiarygodnego dowodu niezmienności pełnych hashy.

Konto techniczne: wskazać dokładny identyfikator z właścicielem; nie zgadywać po nazwie.
Po osobnej zgodzie właściciel korzysta z istniejącej operacji deaktywacji użytkownika,
która unieważnia sesje. Potwierdzić active=false, brak sesji, odmowę logowania i ważność
konta właściciela. Lokalna regresja: test_deactivate_sessions_and_protect_last_manager.
Nie twierdzić, że stan rzeczywistego konta został sprawdzony w tej sesji.
Rollback wdrożenia: poprzedni zatwierdzony commit; flagi Meta nadal wyłączone;
nie wykonywać destrukcyjnego downgrade inboxa, zachować zapisane zdarzenia.

## Etap 4: konfiguracja Meta Developers — tylko przygotowana

Ścieżka: Facebook Login for Business / config_id (Unified Login), nie Instagram Login.
Wartości poświadczeń wpisuje właściciel przez bezpieczny panel, nigdy przez rozmowę.
Nazwy zmiennych i semantyka są w backend/meta.py i backend/meta_flags.py;
sprawdzając panel wolno raportować wyłącznie ustawione/puste/zły format.
Wszystkie flagi pozostają wyłączone, w szczególności META_DM_TRANSPORT_ENABLED=false.
Nie odczytywano ani nie zmieniano ustawień produkcyjnych.
Przygotowane URI (zgodność rzeczywistego panelu niezweryfikowana):
https://ai-focus-3-0.onrender.com/api/meta/oauth/callback
Pozostałe URI przygotowane z kodu (nie skonfigurowano ich w panelu):
- Webhook GET/POST: https://ai-focus-3-0.onrender.com/api/meta/webhook
- Deauthorize: https://ai-focus-3-0.onrender.com/api/meta/deauthorize
- Data deletion: https://ai-focus-3-0.onrender.com/api/meta/data-deletion
- Privacy Policy: https://ai-focus-3-0.onrender.com/api/meta/privacy
- Zakresy kodu v26.0: instagram_basic, instagram_manage_messages.
Dokumentacja historycznej weryfikacji: docs/meta/3.0.4 oraz backend/meta.py.
Lokalny preflight: scripts/meta_local_preflight.py, przyjmuje jawny syntetyczny słownik;
nie odczytuje środowiska produkcyjnego i nie sprawdza rzeczywistych wartości.
Format META_ENCRYPTION_KEY: urlsafe-base64 32-bajtowego klucza akceptowanego przez Fernet.
Nie generować ani nie rotować produkcyjnego klucza podczas tego etapu.
Wymagane: aplikacja Development, dopuszczone konto testowe/rola testera,
zatwierdzony IG user ID, minimalne zakresy i właściciel sesji, HTTPS callback,
Privacy Policy, deauthorize/data deletion oraz weryfikacja podpisów.
Aktualność dokumentacji i konfiguracja panelu wymagają ponownego potwierdzenia;
nie raportujemy wykonania rzeczywistego OAuth na podstawie mocków.

## Etapy 5–6 i punkt zatrzymania

Mocki nie dowodzą działania konta Instagram. Realny test wymaga osobnego dopuszczenia
kont testowych, autoryzacji i połączeń do Meta; w tej sesji nie wykonywać.
Webhooki wyłącznie zapisują zdarzenia; żadnych automatycznych odpowiedzi.
Etap 7 nie rozpoczęty. Wysyłka wymaga osobnej wyraźnej zgody.

# Zasady danych — materiał dla administratora, faza 1

Administratorem danych klientów jest operator CRM. Przed użyciem produkcyjnym uzupełnia tożsamość, kontakt i informację z art. 13/14 RODO; prowadzi rejestr czynności oraz umowy z procesorami (Render; dostawca AI tylko po odrębnym zatwierdzeniu).

Publiczny profil firmy nie oznacza zgody na marketing. Podstawa przetwarzania danych w CRM (np. prawnie uzasadniony interes po teście równowagi) wymaga udokumentowania; nie zastępuje zgody wymaganej dla wybranego kanału komunikacji handlowej na podstawie polskiego Prawa komunikacji elektronicznej. Bez potwierdzenia podstawy i wymaganej zgody agent przygotowuje wyłącznie szkic. Źródło i data pozyskania: source_url i created_at; data utworzenia CRM nie jest automatycznie datą publikacji źródła.

Rezygnacja: opiekun ustawia status do_not_contact, zapisuje aktywność z datą i zakresem sprzeciwu. Worker blokuje analizę kontaktową; żaden kanał wysyłki nie jest aktywny. Minimalny wpis blokujący może wymagać dalszego przechowania dla respektowania sprzeciwu. Nie usuwać go bez oceny administratora.

Minimalizacja: dane służbowe potrzebne do relacji, bez danych szczególnych kategorii. Nie wklejać informacji prywatnych ani wrażliwych do notatek. Handlowiec widzi tylko przypisane salony; odczyty API logują identyfikator konta, szablon ścieżki, czas i wynik, bez treści i parametrów. Historia mutacji CRM i wynik agenta są w PostgreSQL. Logi Render mają ograniczoną retencję i nie zastępują niezależnego, odpornego na zmiany archiwum audytu.

Proponowana retencja do zatwierdzenia: nieaktywne leady przegląd co 90 dni, usunięcie/anonymizacja po 12 miesiącach bez uzasadnienia dalszego przetwarzania; kopie 30 dni; logi bezpieczeństwa 30–90 dni. To polityka projektowa — automatyczne usuwanie danych CRM nie jest włączone. Żądania dostępu/sprostowania/usunięcia/ograniczenia rozpatruje właściciel, po weryfikacji tożsamości, z uwzględnieniem kopii i obowiązków prawnych. Brak samoobsługowego portalu DSR i automatycznej retencji.

Przed uruchomieniem modelu: zatwierdzić procesora, DPA, region/transfery i okresy retencji. Obecny adapter przekazuje tylko wynik liczbowy, priorytet, wersję reguł i nazwy brakujących pól; nie przekazuje nazw salonów, kontaktów, adresów, historii ani swobodnego tekstu. AI_PAID_PROCESSING_APPROVED jest domyślnie false. API nie służy do profilowania osób ani automatycznych decyzji prawnych.

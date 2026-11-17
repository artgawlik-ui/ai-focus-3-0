# Plan Meta — bez wykonywania rzeczywistych operacji

Źródła oficjalne sprawdzono w sesji 002, 2026-11-01:
- https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-unified-login/get-started
- https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-unified-login/permissions
- https://developers.facebook.com/documentation/instagram-platform/webhooks/setup
Dowody HTTP/SHA: ../session-002/documentation-evidence.json. Nie odpytywano Graph API.

## A. Development OAuth — wymaga odrębnego dopuszczenia testu

Konfiguracja Unified Login/Facebook Login for Business, Meta App ID/Secret, config_id,
SUAT i kod Graph v26.0; scopes instagram_basic/instagram_manage_messages.
App należąca do business portfolio; odrębne profesjonalne konto testowe, rola tester
oraz przyjęte zaproszenie. Konto docelowe właściciela nie jest automatycznie kontem testowym.
Standard Access dotyczy osób z rolą; nie obejmuje dowolnych klientów.
Wymagany zatwierdzony testowy HTTPS callback i bezpieczny magazyn klucza/tokenów.
Nie używać produkcyjnego callbacka ani zmieniać flag produkcji bez osobnej zgody;
nie utworzono testowego publicznego hostingu, tunelu ani nowej płatnej usługi.

Scenariusz po dopuszczeniu: właściciel zalogowany w tej samej sesji Safari → state/nonce
→ ekran zgody Meta zatwierdzony osobiście → server-side wymiana kodu → zgodne App ID,
IG User ID i minimalne scopes → Fernet w DB → lokalny disconnect, bez DM/subskrypcji.
Błędy odmowy/niezgodnego konta/replay/wygaśnięcia muszą odrzucać autoryzację.
Status obecny: mocki/local PASS, rzeczywisty test BLOCKED, nie wygenerowano tokenów.

## B. Webhook — osobna bramka Live

Dokumentacja setup wymaga published/Live dla notifications app users i business
verification dla production access. Development OAuth nie potwierdza dostawy webhooka.
Nie zakładamy wyjątku dla testerów bez potwierdzenia dopuszczonego scenariusza przez Meta.
Advanced Access/App Review są wymagane dla klientów bez roli i odpowiednich permissions;
Live nie jest automatycznym pozwoleniem na kontakt z klientami.

Po osobnych zgodach na Live/zakres/testowy callback: GET challenge z verify token,
POST surowe body + X-Hub-Signature-256, commit trwałego inboxa przed 200, duplikaty,
retry/restart/dead-letter, historyczne CRM, usunięcie/rezygnacja. Testuje się wyłącznie
zatwierdzone konta i fixture bez wysyłania przez aplikację. Nie inicjować rzeczywistych
wiadomości testowych w ramach sesji 003. Webhook nigdy nie odpowiada automatycznie.
Subscribed field tylko messages; brak statusu delivery/read bez dowodu implementacji/API.
Transport DM niezależnie false i nie jest częścią zgody OAuth ani webhook.

Warunki STOP: brak zgody właściciela, nieautoryzowany IG ID, dodatkowy scope,
nieznany typ tokenu, wyciek, niezgodny podpis, brak idempotencji/commit-before-200,
nieuzgodnione przechowywanie/retencja treści lub marketingowa podstawa prawna.
RODO: minimalizacja, kontrola dostępu, trwały opt-out, osobna retencja failed/DLQ,
usunięcia respektowane także po restore. Dostęp API nie oznacza zgody na marketing.

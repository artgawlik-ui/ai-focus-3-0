"""Explainable CRM-only qualification. Inputs are data, never instructions."""
from datetime import datetime, timedelta, timezone

RULE_VERSION='glogow-b2b-1'

def analyze(salon, history, evidence='', *, at=None):
    at=at or datetime.now(timezone.utc)
    sources=[{'id':'crm:'+salon.id,'type':'crm','acquired_at':salon.created_at,'url':salon.source_url or None,'verification':'operator_entered'}]
    reasons=[]
    def criterion(name,points,source,explanation):
        reasons.append({'criterion':name,'points':points,'source':source,'explanation':explanation})
    specialization=salon.specialization.strip()
    if specialization:
        criterion('specialization_recorded',20,'crm:'+salon.id,'Zapisano specjalizację; dopasowanie portfolio wymaga rozmowy, nie jest faktem potwierdzonym przez AI.')
    potential=salon.potential
    criterion('declared_monthly_potential',40 if potential>=3000 else 25 if potential>=1500 else 10 if potential>0 else 0,'crm:'+salon.id,'Deklaracja CRM, nie prognoza zakupów: '+str(potential)+' PLN.' if potential else 'brak informacji')
    criterion('sales_stage',25 if salon.stage in ('offer','negotiation') else 15 if salon.stage=='discovery' else 0,'crm:'+salon.id,'Etap zapisany przez opiekuna: '+salon.stage)
    city=salon.city.casefold().strip()
    criterion('operational_region',15 if city=='głogów' else 0,'crm:'+salon.id,'Głogów — region startowy.' if city=='głogów' else 'Odległość od Głogowa: brak informacji; brak geokodowania.')
    cutoff=(at-timedelta(days=7)).isoformat()
    recent=[a for a in history if a.kind in ('call','visit','follow_up') and a.created_at>cutoff]
    for a in history:
        sources.append({'id':'activity:'+a.id,'type':'crm_activity','acquired_at':a.created_at,'kind':a.kind})
    if evidence.strip():
        sources.append({'id':'operator_evidence','type':'unverified_operator_text','acquired_at':at.isoformat(),'verification':'unverified','used_for_scoring':False})
    reply_reviews=[]
    for activity in history:
        if activity.kind!='email_received':continue
        text=activity.body.casefold()
        category='opt_out_review' if any(t in text for t in ('nie kontakt','usuń moje','usun moje','nie życzę','nie zycze')) else 'meeting_interest_review' if any(t in text for t in ('spotkanie','termin','wizyta')) else 'needs_human_review'
        reply_reviews.append({'category':category,'source':'activity:'+activity.id,'requires_owner_review':True,'automatic_crm_change':False})
    score=sum(r['points'] for r in reasons)
    priority='A+' if score>=80 else 'A' if score>=60 else 'B' if score>=30 else 'C'
    optout_reviews=[r for r in reply_reviews if r['category']=='opt_out_review']
    blocked=salon.status=='do_not_contact' or bool(optout_reviews)
    if blocked:priority='C'
    next_step='Uszanuj rezygnację; nie kontaktuj się.' if blocked else 'Odczekaj: przejrzyj historię; kontakt w ostatnich 7 dniach — nie ponawiaj bez decyzji właściciela.' if recent else 'Potwierdź potrzeby i podstawę prawną kontaktu; przygotuj propozycję rozmowy do zatwierdzenia.'
    if blocked:criterion('contact_opt_out',0,optout_reviews[0]['source'] if optout_reviews else 'crm:'+salon.id,'Zakaz kontaktu lub potencjalna rezygnacja wymagają przeglądu; szkic zablokowany.')
    draft='' if blocked else ('Dzień dobry! Reprezentuję NAK Hair i muk Haircare. '+('Chętnie porozmawiam o potrzebach związanych ze specjalizacją wpisaną w naszym CRM: '+specialization+'. ' if specialization else '')+'Czy byliby Państwo otwarci na krótką rozmowę o potrzebach salonu '+salon.name+'? Termin dopasujemy do Państwa dostępności.')
    return {'reply_reviews':reply_reviews,'appointment_recommendation':{'status':'needs_owner_approval','source':'crm:'+salon.id,'next_step':'Zapytaj o dostępność i sprawdź kalendarz przed proponowaniem terminu.','creates_event':False},'engine':'rules','rules_version':RULE_VERSION,'generated_at':at.isoformat(),'priority_suggestion':priority,'score':score,'criteria':reasons,'sources':sources,'missing_information':[k for k,v in [('specialization',specialization),('source_url',salon.source_url),('purchase_potential',potential)] if not v],'unknown_value':'brak informacji','evidence_status':'provided_unverified' if evidence else 'crm_only','next_step':next_step,'next_step_sources':['crm:'+salon.id]+['activity:'+a.id for a in recent],'draft':draft,'draft_status':'draft','requires_owner_approval':True,'sent':False,'appointment_created':False,'warning':'Szkic i rekomendacja. Dane CRM wymagają weryfikacji. Wysyłka i wizyta wymagają zgody właściciela.'}

def minimal_model_context(analysis):
    """No names, contacts, free-text evidence, notes, or customer replies leave CRM."""
    return {'rules_version':analysis['rules_version'],'priority':analysis['priority_suggestion'],'score':analysis.get('score'),'missing_fields':analysis['missing_information'],'task':'Zaproponuj neutralne pytania o potrzeby salonu; nie dodawaj faktów ani danych osobowych.'}

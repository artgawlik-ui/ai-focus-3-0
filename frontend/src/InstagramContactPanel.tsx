import {useEffect,useState,useRef} from 'react';
export function InstagramContactPanel({salonId,api,onChange}:{salonId:string;api:(path:string,options?:RequestInit)=>Promise<any>;onChange:()=>Promise<void>}){
 const [state,setState]=useState<any>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[evidence,setEvidence]=useState(''),[note,setNote]=useState(''),[confirmed,setConfirmed]=useState(false),[initiated,setInitiated]=useState(false);
 const base='/salons/'+salonId;
 const generation=useRef(0),inFlight=useRef(false),operation=useRef({payload:'',id:''});
 const load=async(version:number)=>{const result=await api(base+'/instagram-contact');if(version===generation.current)setState(result)};
 useEffect(()=>{const version=++generation.current;setState(null);load(version).catch(()=>{if(version===generation.current)setError('Nie można odczytać historii kontaktu.')});return()=>{generation.current++}},[salonId]);
 const act=async(fn:()=>Promise<any>)=>{
  if(inFlight.current)return;
  inFlight.current=true;const version=generation.current;setBusy(true);setError('');
  try{await fn();if(version!==generation.current)return;await load(version);if(version!==generation.current)return;await onChange();if(version===generation.current){setConfirmed(false);setInitiated(false)}}
  catch(e){if(version===generation.current){setError((e as Error).message);try{await load(version)}catch{}}}
  finally{inFlight.current=false;if(version===generation.current)setBusy(false)}
 };
 const record=async(action:string,draftId:string)=>{
  const payload={draft_id:draftId,action,note,confirmed,customer_initiated:initiated};const key=JSON.stringify(payload);
  if(operation.current.payload!==key)operation.current={payload:key,id:crypto.randomUUID()};
  return api(base+'/instagram-events',{method:'POST',body:JSON.stringify({...payload,request_id:operation.current.id})});
 };
 if(!state)return error?<p role="alert">{error}</p>:null;
 const drafts=state.events.filter((e:any)=>e.kind==='sales_draft'),draft=drafts.at(-1);
 const related=state.events.filter((e:any)=>e.details.draft_id===draft?.id),sent=related.some((e:any)=>e.kind==='instagram_manual'),answered=related.some((e:any)=>['instagram_reply_manual','sales_refused'].includes(e.kind));
 const refused=related.some((e:any)=>e.kind==='sales_refused');
 const labels:Record<string,string>={sales_profile:'Profil zweryfikowany przez operatora',sales_draft:'Szkic · nie wysłano',sales_not_sent:'Nie wysłano · deklaracja operatora',instagram_manual:'Wysłano ręcznie · deklaracja właściciela',instagram_reply_manual:'Odpowiedział · zapis ręczny',sales_refused:'Odmowa · kontakt zablokowany'};
 return <section aria-label="Ręczny kontakt Instagram" aria-busy={busy} className="card padded"><h3>Kontakt Instagram</h3><p>Nadawca: {state.sender}. Aplikacja nie loguje się i nie wysyła DM. Link nie potwierdza wysyłki.</p>{state.profile_url?<a className="secondary" href={state.profile_url} target="_blank" rel="noopener noreferrer">Otwórz profil Instagram</a>:<p>Uzupełnij poprawny profil Instagram w CRM.</p>}
 {error&&<p role="alert">{error}</p>}{state.blocked?<p>Kontakt zablokowany — uszanuj rezygnację.</p>:<>
 {!state.profile_verified&&state.profile_url&&<form onSubmit={e=>{e.preventDefault();act(()=>api(base+'/verify-instagram',{method:'POST',body:JSON.stringify({profile:state.profile_url,evidence,identity_confirmed:true})}))}}><label>Dowód ręcznej weryfikacji tożsamości i specjalizacji<input disabled={busy} required minLength={10} maxLength={500} value={evidence} onChange={e=>setEvidence(e.target.value)}/></label><button disabled={busy}>Potwierdzam zgodność profilu z salonem</button></form>}
 {state.profile_verified&&!sent&&<button className="secondary" disabled={busy} onClick={()=>act(()=>api(base+'/prepare-instagram',{method:'POST'}))}>Przygotuj indywidualny szkic DM</button>}
 {draft&&<><blockquote>{draft.details.text}</blockquote><p>Szkic nie jest wysyłką. Zanim rozpoczniesz kontakt, sprawdź historię, podstawę prawną i zasady komunikacji.</p><label>Wynik kontaktu lub powód niewysłania<textarea disabled={busy} maxLength={2000} minLength={3} value={note} onChange={e=>setNote(e.target.value)}/></label><label><input disabled={busy} type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>Potwierdzam rzeczywiste zdarzenie; dla wysyłki również uprawnienie do kontaktu i akceptację właściciela</label>{sent&&!answered&&<label><input disabled={busy} type="checkbox" checked={initiated} onChange={e=>setInitiated(e.target.checked)}/>Klient sam zainicjował uzgodnienie terminu</label>}
 <div className="toolbar">{(sent?refused?[]:answered?['refused']:['replied','refused']:['not_sent',...(state.can_confirm_sent?['manual_sent']:[])]).map(action=><button key={action} className="secondary" disabled={busy||!confirmed||note.trim().length<3} onClick={()=>act(()=>record(action,draft.id))}>{{not_sent:'Nie wysłano',manual_sent:'Wysłano ręcznie',replied:'Odpowiedział',refused:'Odmowa / nie kontaktować'}[action]}</button>)}</div></>}
 </>}
 <div className="timeline">{state.events.map((e:any)=><article key={e.id}><small>{labels[e.kind]} · {new Date(e.at).toLocaleString('pl-PL')} · autor {e.author_id}</small><p>{e.details.note||e.details.evidence||''}</p><small>Źródło: deklaracja operatora; brak potwierdzenia API.</small></article>)}</div></section>
}

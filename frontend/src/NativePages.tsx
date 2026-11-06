import {useEffect,useState} from 'react';
export function PageControls({label,page,change}:{label:string;page:any;change:(offset:number)=>void}){
 if(!page)return null;
 return <nav className="toolbar" aria-label={'Strony '+label}><button type="button" className="secondary" disabled={!page.offset} onClick={()=>change(Math.max(0,page.offset-page.limit))}>Poprzednia strona {label}</button><span>{page.total?`${page.offset+1}–${Math.min(page.offset+page.items.length,page.total)}`:'0'} / {page.total}</span><button type="button" className="secondary" disabled={!page.has_more} onClick={()=>change(page.offset+page.limit)}>Następna strona {label}</button></nav>
}
export function ContactPicker({api,label,onReady}:{api:(p:string)=>Promise<any>;label:string;onReady?:(ready:boolean)=>void}){
 const [q,setQ]=useState(''),[page,setPage]=useState<any>(null),[offset,setOffset]=useState(0),[selected,setSelected]=useState(''),[error,setError]=useState(''),[loading,setLoading]=useState(true);
 useEffect(()=>{onReady?.(!loading&&!!selected)},[loading,selected,onReady]);
 useEffect(()=>{let active=true;setLoading(true);const timer=setTimeout(()=>{api('/focus-calendar/contacts/page?'+new URLSearchParams({search:q,offset:String(offset),limit:'20'})).then(p=>{if(active){setPage(p);setLoading(false);setError('');if(!p.items.some((r:any)=>r.salon_id===selected))setSelected(p.items[0]?.salon_id||'')}}).catch(e=>{if(active){setError(e.message);setLoading(false)}})},250);return()=>{active=false;clearTimeout(timer)}},[q,offset]);
 return <div><label>Wyszukaj — {label}<input type="search" value={q} onChange={e=>{setQ(e.target.value);setOffset(0)}}/></label><label>{label}<select name="salon" aria-label={label} required disabled={loading} aria-busy={loading} value={selected} onChange={e=>setSelected(e.target.value)}>{page?.items.map((r:any)=><option key={r.salon_id} value={r.salon_id}>{r.salon_name}</option>)}</select></label>{error&&<p role="alert">{error}</p>}<PageControls label={label} page={page} change={setOffset}/></div>
}

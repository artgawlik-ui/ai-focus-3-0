"""Complete viewport sequences avoid WebKit's 32767-device-pixel bitmap limit."""
import json,math
from pathlib import Path


def capture_page(page,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    original=page.evaluate('({x:scrollX,y:scrollY})')
    tiles=[];target=0
    try:
        page.evaluate('document.fonts.ready')
        for index in range(200):
            page.evaluate('(y)=>window.scrollTo({left:0,top:y,behavior:"instant"})',target)
            geometry=page.evaluate('''()=>({y:scrollY,width:innerWidth,height:innerHeight,
                documentHeight:Math.max(document.documentElement.scrollHeight,document.body.scrollHeight),
                dpr:devicePixelRatio})''')
            if max(geometry['width'],geometry['height'])*geometry['dpr']>30000:
                raise ValueError('Viewport exceeds the safe bitmap dimensions')
            if tiles and geometry['y']<=tiles[-1]['y']:
                raise RuntimeError('Screenshot viewport did not advance')
            if tiles and geometry['y']>tiles[-1]['y']+tiles[-1]['height']:
                raise RuntimeError('Screenshot coverage has a gap')
            name=path if index==0 else path.with_name(path.stem+f'.part-{index+1:03d}'+path.suffix)
            # Deliberately never request a full-document bitmap, regardless of DPR.
            page.screenshot(path=str(name),full_page=False)
            tiles.append({'file':name.name,**geometry})
            after=page.evaluate('Math.max(document.documentElement.scrollHeight,document.body.scrollHeight)')
            if geometry['y']+geometry['height']>=after:break
            next_target=min(geometry['y']+max(1,math.floor(geometry['height']/2)),after-geometry['height'])
            if next_target<=geometry['y']:raise RuntimeError('Screenshot scrolling stopped before the document end')
            target=next_target
        else:raise RuntimeError('Screenshot sequence exceeded 200 viewports; no truncation allowed')
        manifest={'capture':'overlapping_viewports','complete':True,'document_height':after,'tiles':tiles}
        path.with_suffix('.tiles.json').write_text(json.dumps(manifest,indent=2))
        return manifest
    finally:
        page.evaluate('(p)=>window.scrollTo({left:p.x,top:p.y,behavior:"instant"})',original)


def screenshot_probe(context,label,directory):
    """Synthetic long document, no app state or network. Runs in each required engine."""
    page=context.new_page()
    try:
        dpr=page.evaluate('devicePixelRatio');height=math.ceil(33000/dpr)+100
        page.set_content(f'<html><meta name="viewport" content="width=device-width, initial-scale=1"><body style="margin:0"><main style="height:{height}px">Synthetic screenshot regression</main></body></html>')
        legacy_limit_reproduced=False
        if label=='webkit-iphone':
            try:page.screenshot(full_page=True)
            except Exception as error:
                if '32767' not in str(error):raise
                legacy_limit_reproduced=True
        page.evaluate('window.scrollTo(0,50)');before=page.evaluate('scrollY')
        manifest=capture_page(page,Path(directory)/(label+'-long-document.png'))
        assert manifest['tiles'][0]['y']==0
        assert manifest['tiles'][-1]['y']+manifest['tiles'][-1]['height']>=manifest['document_height']
        assert page.evaluate('scrollY')==before
        assert manifest['document_height']*dpr>32767
        return {'legacy_limit_reproduced':legacy_limit_reproduced,'tiles':len(manifest['tiles']),'document_device_height':math.ceil(manifest['document_height']*dpr)}
    finally:page.close()

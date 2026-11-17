"""Geometry and fail-closed coverage tests; real engine probe runs in E2E."""
import json
from pathlib import Path
import pytest
from tests.browser_capture import capture_page

class Page:
    def __init__(self,height=12000,dpr=3):self.height=height;self.dpr=dpr;self.y=50;self.fail=False
    def evaluate(self,expression,arg=None):
        if expression=='({x:scrollX,y:scrollY})':return {'x':0,'y':self.y}
        if expression=='document.fonts.ready':return None
        if 'window.scrollTo' in expression:
            self.y=arg['y'] if isinstance(arg,dict) else max(0,min(arg,self.height-844));return None
        if 'documentHeight:' in expression:return {'y':self.y,'width':390,'height':844,'documentHeight':self.height,'dpr':self.dpr}
        if expression.startswith('Math.max'):return self.height
        raise AssertionError('Unexpected browser evaluation')
    def screenshot(self,*,path,full_page):
        assert full_page is False
        if self.fail:raise RuntimeError('Synthetic screenshot failure')
        Path(path).write_bytes(b'synthetic')

@pytest.mark.parametrize('height,dpr',[(800,3),(12000,3),(40000,1)])
def test_capture_covers_the_whole_document_without_a_giant_bitmap(tmp_path,height,dpr):
    p=Page(height,dpr);p.y=0 if height<844 else 50;before=p.y
    result=capture_page(p,tmp_path/'page.png')
    assert result['complete'] and result['tiles'][0]['y']==0
    assert result['tiles'][-1]['y']+844>=height and p.y==before
    for first,second in zip(result['tiles'],result['tiles'][1:]):assert second['y']<=first['y']+first['height']
    assert json.loads((tmp_path/'page.tiles.json').read_text())==result

def test_capture_restores_scroll_after_error_and_does_not_claim_completion(tmp_path):
    p=Page();p.fail=True
    with pytest.raises(RuntimeError,match='Synthetic'):capture_page(p,tmp_path/'failed.png')
    assert p.y==50 and not (tmp_path/'failed.tiles.json').exists()

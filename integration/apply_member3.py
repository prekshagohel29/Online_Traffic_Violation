"""Integrate Member 3 routes into the exact shared college baseline, with backups."""
import ast,hashlib,json,sys
from pathlib import Path
from datetime import datetime,timezone

ADMIN_NAMES={'analytics','users','provision','audit_log','policy','set_policy','create_device','revoke_device'}
REPORT_NAMES={'demo_expr','scoped','filtered','profile','serialize','cases','case_filters','case','overview'}

def span(node):return min([node.lineno]+[d.lineno for d in node.decorator_list])-1,node.end_lineno
def remove_nodes(text,nodes):
    lines=text.splitlines(keepends=True)
    for a,b in sorted([span(n) for n in nodes],reverse=True):del lines[a:b]
    return ''.join(lines)

def transformed_app(text):
    tree=ast.parse(text)
    admin=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='register_admin_routes')
    video=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='register_video_routes')
    selected=[n for n in admin.body if isinstance(n,ast.FunctionDef) and n.name in ADMIN_NAMES]
    assert {n.name for n in selected}==ADMIN_NAMES,'Unexpected admin baseline'
    health=next(n for n in video.body if isinstance(n,ast.FunctionDef) and n.name=='operator_health')
    result=remove_nodes(text,selected+[health])
    marker='def register_admin_routes(app,engine,throttle):\n'
    assert marker in result
    result=result.replace(marker,marker+'    from .member3_admin import register_member3_admin\n    register_member3_admin(app,engine)\n',1)
    marker="    @app.get('/health')\n"
    assert marker in result
    result=result.replace(marker,'    from .member3_admin import register_member3_health\n    register_member3_health(app,engine,model_health)\n'+marker,1)
    return result

def transformed_experience(text):
    tree=ast.parse(text);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='register_experience')
    selected=[n for n in fn.body if isinstance(n,ast.FunctionDef) and n.name in REPORT_NAMES]
    assert {n.name for n in selected}==REPORT_NAMES,'Unexpected reporting baseline'
    result=remove_nodes(text,selected)
    marker='    from .app import role, fetch, record, owner, audit, json_body, string, plate, page_query\n'
    assert marker in result
    return result.replace(marker,marker+'    from .member3_reporting import register_member3_reporting\n    profile=register_member3_reporting(app,engine)\n',1)

def main():
    root=Path(__file__).resolve().parents[1]
    spec=json.loads((root/'integration/member3_baseline.json').read_text())
    replacements={}
    for name,transform in [('backend/app.py',transformed_app),('backend/experience.py',transformed_experience)]:
        path=(root/name).resolve()
        if not path.is_relative_to(root) or not path.is_file():raise SystemExit('Merge the shared core first; missing '+name)
        content=path.read_bytes();digest=hashlib.sha256(content).hexdigest()
        if digest==spec[name]['after_sha256']:continue
        if digest!=spec[name]['before_sha256']:raise SystemExit('Shared file differs from the agreed baseline; review the patch manually: '+name)
        updated=transform(content.decode('utf-8').replace('\r\n','\n')).encode('utf-8')
        assert hashlib.sha256(updated).hexdigest()==spec[name]['after_sha256']
        replacements[path]=updated
    for name in ['backend/member3_admin.py','backend/member3_reporting.py']:
        if not (root/name).is_file():raise SystemExit('Missing Member 3 source: '+name)
    if not replacements:print('Member 3 integration is already applied.');return
    backup=root/'data/member3-integration-backups'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    for path,content in replacements.items():
        original=backup/path.relative_to(root);original.parent.mkdir(parents=True,exist_ok=True);original.write_bytes(path.read_bytes())
        path.write_bytes(content)
    print('Integrated Member 3 routes. Shared auth, citizen and RTO handlers retained. Backups: '+str(backup))
if __name__=='__main__':main()

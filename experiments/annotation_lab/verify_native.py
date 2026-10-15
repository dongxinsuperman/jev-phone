"""Capture SDK native enhancement off/on on a prepared page, without tapping."""
import argparse,copy,io,json,time
from pathlib import Path
from PIL import Image
from jev_phone import configure
from jev_phone.settings import visual_enhancement_enabled
from jev_phone.adapters import IOSAdapter,HarmonyAdapter
from jev_phone.core import annotate,candidates_from_tree


def verify(adapter,destination):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    previous=visual_enhancement_enabled();rows={};observations={};candidate_sets={}
    try:
        for enabled in (False,True):
            configure(visual_enhancement=enabled);times={}
            def stage(k,f):
                start=time.perf_counter()
                try:return f()
                finally:times[k]=(time.perf_counter()-start)*1000
            observation=adapter.observe(stage);size=Image.open(io.BytesIO(observation.image)).size
            nodes=candidates_from_tree(observation.tree,*size);original=copy.deepcopy(nodes)
            regions=stage('visual_enhancement',lambda:adapter.enhance_annotation(observation,nodes))
            try:rendered=stage('annotation',lambda:annotate(observation.image,nodes,regions));fallback=False
            except (ValueError,TypeError):rendered=annotate(observation.image,nodes);fallback=True
            assert original==nodes,'Enhancement changed candidate payload'
            mode='on'if enabled else'off';observations[mode]=observation;candidate_sets[mode]=nodes
            (destination/(mode+'.jpg')).write_bytes(rendered)
            (destination/(mode+'-tree.xml')).write_text(observation.tree)
            rows[mode]={'timings_ms':times,'candidate_count':len(nodes),'regions':regions,
                'visual_enhancement':observation.metadata.get('visual_enhancement'),
                'render_fallback':fallback,'candidate_payload_unchanged':True}
        # Before/after comparison uses one screenshot, not two different frames.
        on=observations['on'];nodes=candidate_sets['on']
        (destination/'before.jpg').write_bytes(annotate(on.image,nodes))
        (destination/'after.jpg').write_bytes((destination/'on.jpg').read_bytes())
        rows['off_on_click_contract_identical']=[(n['id'],n['bounds'])for n in candidate_sets['off']]==[(n['id'],n['bounds'])for n in nodes]
        (destination/'result.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
        print(json.dumps({'platform':adapter.platform,'same_click_contract':rows['off_on_click_contract_identical'],
            'regions':len(rows['on']['regions']),'status':rows['on']['visual_enhancement'],'timings':rows['on']['timings_ms']},ensure_ascii=False),flush=True)
        assert rows['off_on_click_contract_identical'],'Capture source changed the click contract'
        return rows
    finally:
        configure(visual_enhancement=previous);adapter.close()


if __name__=='__main__':
    import logging
    logging.disable(logging.CRITICAL)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('platform',choices=['ios','harmony']);parser.add_argument('--wda-url',default='http://127.0.0.1:8100')
    parser.add_argument('--session-id');parser.add_argument('--serial');parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    adapter=IOSAdapter(args.wda_url,args.session_id)if args.platform=='ios'else HarmonyAdapter(args.serial)
    verify(adapter,args.output)

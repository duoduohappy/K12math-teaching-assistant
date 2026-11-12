import tempfile
import unittest
from pathlib import Path
import server
from workflow import action

class WorkflowTest(unittest.TestCase):
    def test_full_cycle(self):
        old=server.DB
        with tempfile.TemporaryDirectory() as tmp:
            server.DB=Path(tmp)/'test.db'
            try:
                m=action('material',dict(edition='测试版次',chapter='解方程',source='自编测试材料',text='等式性质'))
                c=action('class',dict(name='测试班',students='S01\nS02\nS03'))
                l=action('lesson',dict(material=m['id'],class_id=c['id'],text='教师审核后的测试教案'))
                a=action('publish',dict(lesson=l['id'],topic='移项',count=3))
                payload=dict(assignment=a['id'],student='S01',answers={q['id']:q['answer'] for q in a['questions']})
                action('submit',payload)
                with self.assertRaises(ValueError): action('submit',payload)
                with self.assertRaises(ValueError): action('submit',dict(payload,student='UNKNOWN'))
                r=action('report',dict(assignment=a['id']))
                self.assertEqual(r['missing'],['S02','S03'])
                self.assertEqual(r['analysis']['summary'][0]['rate'],100)
                self.assertEqual(r['material']['id'],m['id'])
                resource=action('resource',dict(material=m['id'],title='导学单',content='依据等式性质求解'))
                self.assertEqual(resource['chapter'],'解方程')
                activity=action('activity',dict(lesson=l['id'],title='符号变化讨论',notes='需进一步追问'))
                self.assertEqual(activity['class_id'],c['id'])
                review=action('review',dict(assignment=a['id'],student='S01',score=85,comment='补充步骤'))
                self.assertEqual(review['score'],85)
                overview=action('lesson-overview',dict(lesson=l['id']))
                self.assertEqual(overview['classroom']['id'],c['id'])
                self.assertEqual(len(overview['assignments']),1)
                published=action('publish-grades',dict(assignment=a['id']))
                self.assertEqual(published['grades'][0]['final_score'],85)
                action('review',dict(assignment=a['id'],student='S01',score=90))
                self.assertEqual(action('report',dict(assignment=a['id']))['publication']['grades'][0]['final_score'],85)
                self.assertEqual(action('publish-grades',dict(assignment=a['id']))['grades'][0]['final_score'],90)
                self.assertEqual(len(action('unit-plan',dict(material=m['id'],class_id=c['id']))['lessons']),4)
                self.assertEqual(len(action('quality-check',dict(lesson=l['id']))['checks']),5)
                self.assertEqual(len(action('classroom-analysis',dict(lesson=l['id']))['activities']),1)
                self.assertEqual(action('reflection',dict(assignment=a['id'],notes='复习符号',next_action='补充讲解'))['lesson'],l['id'])
                with self.assertRaises(ValueError): action('intervention',dict(assignment=a['id'],student='S01'))
                wrong=dict(assignment=a['id'],student='S02',answers={q['id']:str(int(q['answer'])+1) for q in a['questions']})
                action('submit',wrong)
                intervention=action('intervention',dict(assignment=a['id'],student='S02'))
                follow=action('report',dict(assignment=intervention['assignment']))
                self.assertEqual(follow['missing'],['S02'])
                with self.assertRaises(ValueError):action('submit',dict(assignment=intervention['assignment'],student='S01',answers={}))
                with self.assertRaises(ValueError): action('review',dict(assignment=a['id'],student='UNKNOWN',score=90))
                with self.assertRaises(ValueError): action('review',dict(assignment=a['id'],student='S01',score=101))
            finally: server.DB=old

import unittest
from server import generate, assess

class CoreTests(unittest.TestCase):
    def test_all_topics_answers_and_grading(self):
        for topic in ['移项','去括号','去分母']:
            qs=generate(topic,20)
            self.assertTrue(all(q['verified'] for q in qs))
            rows=[dict(student='S1',question_id=q['id'],answer=q['answer']+'/1') for q in qs]
            r=assess(rows,qs)
            self.assertEqual(r['summary'][0]['rate'],100)
            rows[0]['answer']=str(int(qs[0]['answer'])+1)
            self.assertEqual(assess(rows,qs)['summary'][0]['rate'],95)

    def test_reject_duplicates_unknown_and_invalid(self):
        qs=generate('移项',1)
        row=dict(student='S1',question_id='Q1',answer='1')
        for rows in [[row,row],[dict(row,question_id='Q99')],[dict(row,answer='1/0')],[]]:
            with self.assertRaises(ValueError): assess(rows,qs)

if __name__=='__main__': unittest.main()

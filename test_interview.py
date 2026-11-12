import unittest
from interview import verify,retrieve

class InterviewTests(unittest.TestCase):
    def test_exact_math(self):
        for eq,x in [('3x+5=17','4'),('2*(x-3)=8','7'),('(x+1)/3=1/2','1/2'),('5x-7=2x+8','5')]:
            self.assertTrue(verify(eq,x)['correct'])
        self.assertFalse(verify('3x+5=17','7')['correct'])

    def test_reject_unsafe_or_nonlinear(self):
        for expr in ['__import__("os")=1','x*x=4','1/x=3','x=x','x**2=4']:
            with self.assertRaises(ValueError):verify(expr,'1')

    def test_retrieval_no_fabricated_source(self):
        m=dict(id='M',text='移项依据是等式性质。',source='自编卡片',edition='演示',chapter='解方程')
        self.assertEqual(retrieve(m,'移项')[0]['source'],'自编卡片')
        self.assertEqual(retrieve(m,'三角函数'),[])

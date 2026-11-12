"""Persistent teaching workflow; published answers never sent to student GET."""
import json
import secrets
from server import connect, generate, assess

def init():
    with connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS workflow(id TEXT PRIMARY KEY, kind TEXT, body TEXT)')

def put(kind, body):
    init()
    ident=secrets.token_hex(6)
    with connect() as c: c.execute('INSERT INTO workflow VALUES(?,?,?)',(ident,kind,json.dumps(body,ensure_ascii=False)))
    return dict(id=ident,kind=kind,**body)

def get(ident):
    init()
    with connect() as c: row=c.execute('SELECT kind,body FROM workflow WHERE id=?',(ident,)).fetchone()
    if not row: raise ValueError('记录不存在')
    return dict(id=ident,kind=row[0],**json.loads(row[1]))

def listing():
    init()
    with connect() as c: rows=c.execute('SELECT id,kind,body FROM workflow ORDER BY rowid DESC').fetchall()
    return [dict(id=r[0],kind=r[1],**json.loads(r[2])) for r in rows]

def action(route,d):
    if route=='lesson-overview':
        lesson=get(d['lesson'])
        if lesson['kind']!='lesson': raise ValueError('请选择已审核教案')
        records=listing(); assignments=[r for r in records if r['kind']=='assignment' and r['lesson']==lesson['id']]
        return dict(lesson=lesson,classroom=get(lesson['class_id']),activities=[r for r in records if r['kind']=='activity' and r['lesson']==lesson['id']],quality=[r for r in records if r['kind']=='quality_check' and r['lesson']==lesson['id']],assignments=[dict(assignment=a,report=action('report',dict(assignment=a['id']))) for a in assignments],reflections=[r for r in records if r['kind']=='reflection' and r['lesson']==lesson['id']])
    if route=='publish-grades':
        a=get(d['assignment'])
        if a['kind']!='assignment': raise ValueError('请选择作业')
        records=listing(); submissions=[s for s in records if s['kind']=='submission' and s['assignment']==a['id']]
        if not submissions: raise ValueError('暂无提交，不能发布成绩')
        reviews={}
        for r in records:
            if r['kind']=='review' and r['assignment']==a['id'] and r['student'] not in reviews: reviews[r['student']]=r
        grades=[]
        for s in submissions:
            details=s['result']['details']; raw=round(100*sum(x['correct'] for x in details)/len(details),1)
            review=reviews.get(s['student'])
            grades.append(dict(student=s['student'],original_score=raw,final_score=review['score'] if review else raw,comment=review['comment'] if review else '',review_id=review['id'] if review else None,source='教师复核' if review else '客观题程序评分'))
        return put('grade_publication',dict(assignment=a['id'],grades=grades,status='已发布',note='发布时成绩快照；后续复核不会自动改变已发布成绩，需重新发布。'))
    if route=='unit-plan':
        m=get(d['material']); cl=get(d['class_id'])
        if m['kind']!='material' or cl['kind']!='class': raise ValueError('教材或班级无效')
        return put('unit_plan',dict(material=m['id'],class_id=cl['id'],title=d.get('title') or m['chapter'],lessons=[dict(order=i+1,title=t,status='待备课') for i,t in enumerate(['等式性质与方程意义','移项与合并同类项','去括号与去分母','应用与单元检测'])],basis=m['source'],note='一元一次方程单元建议序列，须按实际教材进度调整'))
    if route=='quality-check':
        l=get(d['lesson'])
        if l['kind']!='lesson': raise ValueError('请选择教案')
        checks=[dict(name=n,passed=any(k in l['text'] for k in keys)) for n,keys in [('教学目标',['目标']),('课堂活动',['探究','活动','讲解']),('分层任务',['分层','基础','进阶']),('形成性检测',['检测','测验']),('检验与反馈',['检验','反馈'])]]
        return put('quality_check',dict(lesson=l['id'],checks=checks,score=sum(x['passed'] for x in checks)*20,status='待教师确认',note='结构关键词检查，不代表数学正确、课标对齐或教学质量评分'))
    if route=='classroom-analysis':
        l=get(d['lesson'])
        if l['kind']!='lesson': raise ValueError('请选择教案')
        activities=[r for r in listing() if r['kind']=='activity' and r['lesson']==l['id']]
        assignments=[r for r in listing() if r['kind']=='assignment' and r['lesson']==l['id']]
        return put('classroom_analysis',dict(lesson=l['id'],activities=activities,assessments=[dict(id=a['id'],purpose=a['purpose'],report=action('report',dict(assignment=a['id']))) for a in assignments],note='只展示该教案关联活动和检测；没有记录不代表没有教学活动'))
    if route=='intervention':
        a=get(d['assignment']); cl=get(a['class_id']); target=d.get('student','').strip()
        if target and target not in cl['students']: raise ValueError('学生不在本班')
        from interview import action as teaching_action
        result=teaching_action('remedial',dict(assignment=a['id'],student=target))
        if not result['practice']: raise ValueError('未找到已提交的错题，不能自动指派补救')
        students=[target] if target else list(dict.fromkeys(s['student'] for s in listing() if s['kind']=='submission' and s['assignment']==a['id'] and any(not row['correct'] for row in s['result']['details'])))
        pack=put('assignment',dict(lesson=a['lesson'],class_id=a['class_id'],material=a['material'],purpose='补救练习',questions=[dict(q,id=f'Q{i+1}') for i,q in enumerate(result['practice'])],parent=a['id'],target_students=students))
        return put('intervention',dict(parent=a['id'],assignment=pack['id'],students=students,status='已指派',note=result['note']))
    if route=='reflection':
        a=get(d['assignment']); r=action('report',dict(assignment=a['id']))
        return put('reflection',dict(assignment=a['id'],lesson=a['lesson'],summary=r,teacher_notes=d.get('notes',''),next_action=d.get('next_action',''),status='待落实',note='复盘保留原作业证据，不将不同难度练习分数直接解释为学习提升'))
    if route=='review':
        a=get(d['assignment']); cl=get(a['class_id'])
        if d['student'] not in cl['students']: raise ValueError('学生不在本班')
        if not any(r['kind']=='submission' and r['assignment']==a['id'] and r['student']==d['student'] for r in listing()): raise ValueError('该学生尚未提交，不能复核')
        score=float(d['score'])
        if not 0<=score<=100: raise ValueError('分数须在0—100之间')
        return put('review',dict(assignment=a['id'],student=d['student'],score=score,comment=d.get('comment',''),reviewer='本地教师',status='已复核'))
    if route=='activity':
        lesson=get(d['lesson'])
        if lesson['kind']!='lesson': raise ValueError('请选择已审核教案')
        if not d.get('title','').strip(): raise ValueError('请填写活动主题')
        return put('activity',dict(lesson=lesson['id'],class_id=lesson['class_id'],title=d['title'],activity_type=d.get('activity_type','讨论'),notes=d.get('notes',''),status='已记录'))
    if route=='resource':
        if not d.get('title','').strip() or not d.get('content','').strip(): raise ValueError('标题和内容不能为空')
        m=get(d['material'])
        if m['kind']!='material': raise ValueError('请选择教材材料')
        return put('resource',dict(title=d['title'],content=d['content'],material=m['id'],chapter=m['chapter'],resource_type=d.get('resource_type','教学笔记'),status='教师保存'))
    if route=='demo':
        existing=[r for r in listing() if r['kind']=='class' and r.get('demo')]
        if existing: return dict(loaded=True,existing=True)
        m=put('material',dict(book='人教版七年级数学上册',edition='演示版次，待核实',chapter='一元一次方程 · 移项',source='自编演示知识卡 DEMO-01；非教材原文，无官方页码',text='等式两边同时加上或减去同一个数，结果仍相等。将项移到等号另一侧时改变符号。解方程后将结果代入原式检验。',demo=True))
        c=put('class',dict(name='七年级（2）班 · 模拟',students=[f'S{i:02}' for i in range(1,13)],demo=True))
        text='解一元一次方程：移项\n\n教学目标\n理解移项源于等式性质；能够正确移项、合并同类项并代入检验。\n\n复习导入 · 5分钟\n从 x + 3 = 8 出发，追问两边同时减去3为什么保持相等。\n\n例题探究 · 12分钟\n3x + 5 = 17。两边减5，得3x = 12，再除以3，得x = 4。代回验证17 = 17。\n\n易错辨析 · 8分钟\n讨论把 +5 移到右侧为什么变为 -5；请学生写出等式两侧的相同操作。\n\n分层练习 · 10分钟\n基础：2x + 3 = 11；进阶：5x - 7 = 2x + 8。学生互相解释每一步依据。\n\n随堂检测与总结 · 5分钟\n完成移项检测，记录符号变化问题；课后根据答题结果安排巩固。\n\n材料说明\n以上为自编模拟教案，供测试流程，不代表人教版教材原文或官方教案。'
        l=put('lesson',dict(material=m,class_id=c['id'],text=text,approved=True,demo=True))
        for purpose in ['随堂检测','课后作业']:
            a=action('publish',dict(lesson=l['id'],purpose=purpose,topic='移项',count=5))
            for i in range(1,11):
                action('submit',dict(assignment=a['id'],student=f'S{i:02}',answers={q['id']:str(int(q['answer'])+(1 if (i+j)%4==0 or (i>7 and j%2==0) else 0)) for j,q in enumerate(a['questions'])}))
        return dict(loaded=True,students=12,submitted=10,missing=2)
    if route=='material':
        for k in ['edition','chapter','source','text']:
            if not d.get(k,'').strip(): raise ValueError('请完整填写版次、章节、出处与材料')
        return put('material',dict(book='人教版七年级数学上册',**{k:d[k] for k in ['edition','chapter','source','text']}))
    if route=='class':
        students=list(dict.fromkeys(s.strip() for s in d['students'].splitlines() if s.strip()))
        if not students or not d['name'].strip(): raise ValueError('请填写班级与学生编号')
        return put('class',dict(name=d['name'],students=students))
    if route=='lesson':
        m=get(d['material']); cl=get(d['class_id'])
        if m['kind']!='material' or cl['kind']!='class': raise ValueError('教材或班级无效')
        if not d['text'].strip(): raise ValueError('教案不能为空')
        return put('lesson',dict(material=m,class_id=cl['id'],text=d['text'],approved=True))
    if route=='publish':
        lesson=get(d['lesson'])
        if lesson['kind']!='lesson': raise ValueError('请选择已审核教案')
        return put('assignment',dict(lesson=lesson['id'],class_id=lesson['class_id'],material=lesson['material'],purpose=d.get('purpose','课后作业'),questions=generate(d['topic'],d.get('count',5))))
    if route=='submit':
        a=get(d['assignment']); cl=get(a['class_id'])
        if d['student'] not in cl['students']: raise ValueError('学生编号不在本班名册中')
        if a.get('target_students') and d['student'] not in a['target_students']: raise ValueError('本次补救练习未指派给该学生')
        qs=a['questions']; answers=d['answers']
        if any(q['id'] not in answers for q in qs): raise ValueError('请完成全部题目')
        result=assess([dict(student=d['student'],question_id=q['id'],answer=answers[q['id']]) for q in qs],qs)
        init()
        with connect() as c:
            c.execute('BEGIN IMMEDIATE')
            rows=c.execute("SELECT body FROM workflow WHERE kind='submission'").fetchall()
            if any((b:=json.loads(r[0]))['assignment']==a['id'] and b['student']==d['student'] for r in rows): raise ValueError('已经提交，请联系教师处理更正')
            ident=secrets.token_hex(6); body=dict(assignment=a['id'],student=d['student'],answers=answers,result=result)
            c.execute('INSERT INTO workflow VALUES(?,?,?)',(ident,'submission',json.dumps(body,ensure_ascii=False)))
        return dict(received=True)
    if route=='report':
        a=get(d['assignment']); cl=get(a['class_id']); subs=[s for s in listing() if s['kind']=='submission' and s['assignment']==a['id']]
        rows=[dict(student=s['student'],question_id=qid,answer=answer) for s in subs for qid,answer in s['answers'].items()]
        publication=next((r for r in listing() if r['kind']=='grade_publication' and r['assignment']==a['id']),None)
        return dict(assignment=a['id'],material=a['material'],missing=[s for s in a.get('target_students',cl['students']) if s not in {r['student'] for r in subs}],analysis=assess(rows,a['questions']) if rows else None,publication=publication,note='逐题正确率采用原始答题；最终总分采用最近发布快照，两者不混用。')
    raise ValueError('未知操作')

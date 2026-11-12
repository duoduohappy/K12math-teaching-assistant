const loginCover=document.createElement('div');loginCover.style='position:fixed;inset:0;background:linear-gradient(130deg,#123349,#217a72);z-index:10000;display:flex;align-items:center;justify-content:center';loginCover.innerHTML='<section style="width:400px;max-width:90%;padding:35px"><h2>知序 · 教学工作台</h2><p id="accountHint">请登录后继续</p><input id="accountName" placeholder="账号"><input id="accountPassword" type="password" placeholder="密码，至少8位"><button onclick="loginAccount()">登录</button><button id="setupButton" hidden onclick="setupAccount()">创建首位教师</button><p id="accountError" role="alert"></p></section>';document.body.append(loginCover);
async function accountPost(route,data){const r=await fetch('/api/account/'+route,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const v=await r.json();if(!r.ok)throw Error(v.error);return v}function credentials(){return {username:$('accountName').value.trim(),password:$('accountPassword').value}}
async function setupAccount(){try{await accountPost('setup',credentials());await loginAccount()}catch(e){$('accountError').textContent=e.message}}async function loginAccount(){try{await accountPost('login',credentials());location.reload()}catch(e){$('accountError').textContent=e.message}}
async function checkAccount(){
 try {
  const r=await fetch('/api/account');
  if(!r.ok)throw Error('无法获取账号状态，请关闭旧服务并重新启动');
  const v=await r.json();
  if(!v.user){
   $('setupButton').hidden=!v.setup_required;
   $('accountHint').textContent=v.setup_required?'首次使用：填写账号和密码，然后创建首位教师。':'使用教师或学生账号登录';
   return;
  }
  loginCover.remove();
  const b=document.createElement('button');b.textContent=v.user.username+' · 退出';
  b.onclick=async()=>{await accountPost('logout',{});location.reload()};sidebar.append(b);
  if(v.user.role==='student'){
   if(!aid){$('teacher').hidden=true;$('status').textContent='请使用教师提供的作业链接进入答题。'}
   else {let attempts=0;const wait=setInterval(()=>{attempts++;if($('sid')){$('sid').value=v.user.username;$('sid').readOnly=true;clearInterval(wait)}if(attempts>50)clearInterval(wait)},200)}
  }
 }catch(e){$('accountError').textContent=e.message}
}
checkAccount();
const accountSection=document.createElement('section');accountSection.innerHTML='<h3>学生账号管理</h3><p class="product-help">账号须与班级名册中的学生编号一致，例如 S01。当前为单校共用教师空间，尚无教师之间任教范围隔离。</p><input id="newStudent" placeholder="学生编号"><input id="newStudentPassword" type="password" placeholder="初始密码，至少8位"><button onclick="createStudentAccount()">创建学生账号</button>';sections[1].append(accountSection);async function createStudentAccount(){try{await accountPost('create',{username:$('newStudent').value.trim(),password:$('newStudentPassword').value});$('status').textContent='学生账号已创建'}catch(e){$('status').textContent=e.message}}

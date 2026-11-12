# Render 免费演示部署

本部署用于合成数据演示，不用于真实学校生产业务。没有真实教材核验与真实模型效果验证。

1. 将本目录源码推送到仓库根目录，不提交数据库、日志或密码。
2. Render 创建 Blueprint 并连接仓库，使用 render.yaml；或创建 Python Free Web Service。
3. Build Command: `python -m compileall -q .`
4. Start Command: `python cloud_start.py`
5. 在环境变量中设置 DEMO_TEACHER_PASSWORD（至少12位），不要写入仓库。
6. 健康检查 /health，教师工作台 /workflow，教师账号 teacher，密码为上述环境变量。

每次空数据库启动会创建教师账号并载入模拟班级。Render Free 的文件系统不持久，重启、休眠或部署会丢失新操作与账号；此为可重置演示，不承诺保存。空闲后的首次访问可能需要等待冷启动。

云服务的 localhost 不是用户电脑：云端不能使用用户本机 Ollama。当前演示请使用规则/预置模式，不要声称云端模型生成已验证。

仓库公开不等于业务数据公开。教师密码仅发送给指定体验者。当前教师拥有模拟空间编辑权限，不导入真实学生资料。

## 如何运行

将 server 下的 conf_e.json 以及 conf_e.py，移动到config文件夹下并重命名为 conf.json 和 conf.py。

根据自己的情况修改参数

进入虚拟环境后运行 python manage.py migrate

导入初始数据 python manage.py loaddata db.json

默认管理员账户密码为admin  xtadmin123!

在项目目录下执行 python manage.py runserver 即可

运行后在 localhost:8000/api/swagger/下查看 api 文档



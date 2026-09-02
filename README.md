### VPS 到期监控助手 🚀

一个优雅的 VPS 到期日期监控工具，再也不用担心 VPS 续费超期了！通过 Telegram 机器人推送到期提醒，轻松管理多台服务器。

之前发过帖子，功能上还不太行，这次重新打造

演示：https://woniu336.github.io/vps-date/

项目： https://github.com/woniu336/vps-date

## ✨ 特色功能

- 🤖 支持 Telegram 机器人通知（3天内到期触发通知）
- ⏰ 自动定时检查（每天早8点和晚8点）
- 📊 支持批量管理多台服务器
- 🔔 灵活的提醒时间配置，按固定日期还是每月循环
- 💻 支持 GitHub Actions 自动运行
- 🔔多币种汇率更新，免费的API，不要频繁使用





## 🚀 快速开始

下载项目到本地，双击运行

```
run_manager.bat
```

⚠️ 注意：项目有一个bug，vps名称不能用中文，使用中文脚本会报错，你可以在设置好以后退出脚本，在`index.html`改成中文名称即可，

后续不影响使用

⚠️ 前端可点击`index.html`查看，脚本集成了一键推送到Giuhub

有两个地方需要手动修改，

- 修改`vps_manager.py `第53行，修改成你的监控地址，作用是仅在tg通知底部展示
- 把`config.example.json`重命名为`config.json`，目的是测试通知，注意只有即将到期才会触发通知





### 3. 通知部署

1. Fork 本仓库
2. 在仓库设置中添加以下 Secrets：
   - `TELEGRAM_BOT_TOKEN`: 您的 Telegram 机器人 token
   - `TELEGRAM_CHAT_ID`: 您的 Telegram 聊天 ID
3. Actions 会自动在每天早8点和晚8点（北京时间）运行检查



### 4. 钉钉通知

钉钉通知由于我技术太菜，不能整合到项目中，但可以在你服务器上运行使用

下载ding_monitor.py到服务器上运行即可

1. 安装依赖

```
pip install requests
```

修改脚本，添加钉钉通知


2. 测试

```
python3 ding_monitor.py
```


3. 后台运行

```
nohup python3 ding_monitor.py > ding_monitor.out 2>&1 &
```



4. 查看监控

```
ps aux | grep ding_monitor.py
```

停止进程

```
kill <进程ID>
```



## 📝 使用说明

- 运行 `run_manager.bat` 管理您的 VPS 信息
- 运行 `check_expiry.bat`（Windows）快速检查到期状态

### 网页管理

Windows 下双击 `web_manager.bat`，浏览器会自动打开本地管理页面。页面支持：

- 新增、编辑和删除服务器
- 服务器到期时间按任意月数续期
- SSL 证书按独立月数续期（例如服务器续 1 个月、SSL 续 6 个月）
- 保存后直接更新 `index.html`，到期提醒脚本会读取最新数据

关闭命令窗口即可停止本地管理服务。直接双击打开 `index.html` 时仅为预览模式，修改只保存在当前浏览器中，不会写回项目文件。
- 查看 `vps_monitor.log` 了解运行日志
- 通过 `index.html` 可视化查看 VPS 状态



## 📜 开源协议

本项目采用 MIT 协议开源，欢迎自由使用。

## ⭐ 支持项目

如果这个项目对您有帮助，请给它一个 Star！这是对我们最好的鼓励。

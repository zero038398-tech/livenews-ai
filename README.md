# LiveNews AI

面向芯片公司员工的每日AI新闻精选网站，帮助团队快速了解AI领域最新动态。

## 版本历史

### V2（当前版本）

- 前端：https://livenews-ai.github.io
- 后端：https://livenews-ai-backend.onrender.com/api
- 架构：前后端分离部署（GitHub Pages + Render）
- 特性：专业Loading界面、后端冷启动倒计时、健康检查轮询、骨架屏

### V1

- 网址：https://resonant-profiterole-61ce24.netlify.app/
- 架构：Netlify全栈部署
- 问题：Netlify免费额度耗尽后无法继续使用

## 功能特点

- 📰 每日精选10-20条高质量AI新闻
- 🌐 中英对照：左原文、右中文
- 🤖 智能摘要：点击按钮生成简短摘要
- ✅ 真实性验证：S级+多源验证占比≥80%
- 🏷️ 分类标签：AI芯片动态、工具与实战、行业动态、学术精选
- 📅 7天历史：支持查看7天内每天的新闻
- ⏳ 冷启动优化：专业Loading界面 + 后端健康检查轮询 + 倒计时进度条

## 技术栈

- 前端：React 18 + Vite + Tailwind CSS + Zustand
- 后端：Python FastAPI + APScheduler
- 数据库：Neon PostgreSQL（外部持久化）
- AI服务：Groq API（免费Llama模型）
- 部署：GitHub Pages（前端）+ Render（后端）

## 快速开始

### 前端

```bash
npm install
npm run dev
```

### 后端

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
python main.py
```

## API 接口

- `GET /api/news` - 获取新闻列表
- `GET /api/health` - 健康检查
- `POST /api/daily-summary` - 生成每日摘要
- `GET /api/categories` - 获取分类列表
- `POST /api/admin/fetch-news` - 手动抓取新闻
- `POST /api/admin/translate` - 手动翻译
- `POST /api/admin/fill-history` - 补全历史数据
- `POST /api/admin/reset` - 重置并重新抓取

## 数据源

### 英文源
- Hacker News
- ArXiv CS.AI
- Reddit（LocalLLaMA、MachineLearning、ChatGPT）
- OpenAI Blog
- SemiAnalysis

### 中文源
- 机器之心
- 量子位
- 36氪

## 部署架构

```
用户浏览器
    │
    ├──→ GitHub Pages (livenews-ai.github.io)  ← 永不休眠，秒开
    │         ├── 立即显示专业Loading界面
    │         ├── 后台轮询 /api/health
    │         └── 后端就绪后显示新闻
    │
    └──→ Render (livenews-ai-backend.onrender.com)  ← 可能休眠
              ├── /api/health
              ├── /api/news
              └── /api/daily-summary
```

### 推送代码

```bash
git push origin main   # 推到个人仓库 → 触发Render部署
git push org main      # 推到组织仓库 → 触发GitHub Pages部署
```

## 免费方案

本项目使用完全免费的方案：
- Groq API：免费Llama模型
- GitHub Pages：免费静态网站托管（100GB/月带宽）
- Render：免费后端服务（15分钟无访问后休眠）
- Neon PostgreSQL：免费PostgreSQL数据库

## V3 改进方向

### 高优先级
- 自定义域名：购买 livenews-ai.com 等域名，更专业
- 翻译质量优化：当前部分翻译冗长或偏离原意，需优化prompt
- 新闻去重：同一事件多源报道时合并为一条
- 移动端适配：优化手机端浏览体验

### 中优先级
- 用户偏好：保存用户选择的分类和日期到localStorage
- 搜索功能：支持关键词搜索新闻
- 分享功能：生成新闻卡片图片便于分享
- 暗色模式：支持深色/浅色切换
- 邮件订阅：每日自动推送新闻摘要到邮箱

### 低优先级
- 多语言支持：英文界面版本
- PWA离线支持：离线也能查看已加载的新闻
- 后端改用Vercel Serverless：避免冷启动问题
- 新闻评分：用户可以对新闻点赞/收藏

## 经验教训

### 部署平台选择
- Netlify/Vercel免费版有额度限制，国内手机号注册可能受阻
- GitHub Pages免费且无带宽硬限制，适合纯静态前端
- Render免费版15分钟休眠，定时任务在休眠时不执行
- 方案选择时应先调研免费额度、注册限制、国内访问速度

### 开发流程
- 构建产物（dist/、backend/static/）应随git部署，不完全依赖构建命令
- cp -r 在目标目录已存在时行为与预期不同，应先rm -rf再cp
- FastAPI的StaticFiles mount可能与显式路由冲突，优先使用显式路由
- 修改后应在线验证，而非假设本地通过则线上也能通过

### 与AI协作
- 描述问题时提供具体现象（如"看到的是JSON而非HTML"），而非笼统的"不工作"
- 要求AI修改后自我验证，而非直接告知完成
- 涉及部署问题时，要求AI先排查线上实际返回内容，而非只看本地代码
- 多步骤任务应要求AI列出完整计划后再执行，避免遗漏

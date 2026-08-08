# yupeng0512.github.io

这是 `https://yupeng0512.github.io/` 的公开部署仓库。

## 恢复边界

- `main` 分支可直接恢复当前已部署的静态 HTML、JSON、CSS、JavaScript 和图片。
- GitHub Pages 以 `main` 分支根目录作为发布源，不需要额外构建步骤即可恢复现有页面。
- 本仓库目前不包含生成这些文件的 Astro/博客源项目、依赖锁文件或构建配置，因此只能恢复“已发布产物”，不能保证可重新生成相同产物。
- `api/site.json` 中的 Gitalk 已停用；任何客户端秘密、令牌或密码都不得进入静态站点。

## 本地验收

```bash
python3 scripts/validate-static-site.py
gitleaks dir . --no-banner --redact
```

校验器会解析全部 JSON、检查站内静态引用、拒绝被跟踪的 `.DS_Store`，并阻止 Gitalk 客户端秘密重新进入部署产物。

## 冷恢复

```bash
git clone git@github.com:yupeng0512/yupeng0512.github.io.git
cd yupeng0512.github.io
python3 scripts/validate-static-site.py
python3 -m http.server 8000
```

浏览器打开 `http://localhost:8000/`。如需继续开发页面，应先找回或重建独立的源项目，再把构建产物发布到本仓库；不要把本仓库误当成完整源代码备份。

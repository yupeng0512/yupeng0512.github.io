# yupeng0512.github.io

这是 `https://yupeng0512.github.io/` 的公开部署仓库。

## 恢复边界

- `main` 分支可直接恢复当前已部署的静态 HTML、JSON、CSS、JavaScript 和图片。
- GitHub Pages 以 `main` 分支根目录作为发布源，不需要额外构建步骤即可恢复现有页面。
- 当前作品集页面的源项目已定位为公开仓库 [`yupeng0512/personal-card`](https://github.com/yupeng0512/personal-card)，当前已部署作品集对应固定源提交 `10c0ea912ec964cc50af26706571ed2ece88edd8`。
- 历史 Hexo/Aurora 博客源项目仍未定位，因此旧博客部分目前只能恢复“已发布产物”，不能重建原始 Markdown、主题配置和生成链。
- `api/site.json` 中的 Gitalk 已停用；任何客户端秘密、令牌或密码都不得进入静态站点。

机器可读的提交映射、构建命令和比较边界见 [`build-provenance.json`](build-provenance.json)。

## 本地验收

```bash
python3 scripts/validate-static-site.py
python3 -m unittest discover -s tests -p 'test_*.py'
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

浏览器打开 `http://localhost:8000/`。作品集页面应在 `personal-card` 源仓继续开发，再把受控构建产物发布到本仓；历史 Hexo 博客仍需单独找回或重建源项目。不要把部署仓误当成全部内容的完整源代码备份。

## 作品集源构建复验

固定提交内已包含部署时使用的 `src/data/workspace-data.json` 快照。冷恢复时不要运行该历史提交的 `npm run build`，因为它会先扫描构建机周围的工作区并覆盖这份快照。使用以下封闭路径：

```bash
git clone https://github.com/yupeng0512/personal-card.git
cd personal-card
git checkout 10c0ea912ec964cc50af26706571ed2ece88edd8
npm ci --no-audit --no-fund
./node_modules/.bin/astro build
python3 ../yupeng0512.github.io/scripts/compare_portfolio_build.py --source .
```

本轮已在 Node.js `20.19.4`、npm `10.8.2` 上复验。复验要求源构建的 124 个文件全部存在于部署仓：非 HTML 文件逐字节一致；HTML 仅允许 Astro 每次构建产生的非语义 `astro-island uid` 不同。部署仓可以额外保留旧博客、Pages 配置和安全校验文件。

# 半格设计研究室官网

这是一个静态单页官网，入口文件是 `index.html`。

## 本地预览

在 `website` 目录启动本地服务后访问：

```powershell
python -m http.server 4173
```

然后打开：

```text
http://127.0.0.1:4173/
```

## 内容更新

项目文字来自 `02 成果/半格建筑事务所作品集2025版.pdf`，图片来自同名 2025 PPTX。需要重新生成项目数据和压缩图片时，在项目根目录运行：

```powershell
python .\website\tools\build_content.py
```

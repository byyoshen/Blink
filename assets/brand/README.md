# Blink 品牌母版

原始 logo 母版，**不被任何代码或页面引用** —— 仓库实际发布的资产都是从这里派生的。
保留母版是为了以后还能重新派生（换尺寸、改压缩、补新用途），而不必回去找设计文件。

## 母版

| 文件 | 尺寸 | 内容 |
| --- | --- | --- |
| `badge-dark.png` | 1254² | 圆角徽章，白熊 / 近黑底，浮在白画布上 |
| `badge-light.png` | 1254² | 圆角徽章，黑熊 / 米白底，浮在白画布上 |
| `badge-transparent.png` | 1254² | 熊本体，透明背景（心为深色，单用不覆盖双主题） |
| `wordmark-dark.png` | 2170×725 | 熊 + Blink 字标横版，近黑底 |
| `wordmark-light.png` | 2170×725 | 同上，米白底 |
| `wordmark-krystal.png` | 1999×786 | 横版变体，透明背景（当前未使用） |

## 派生出的发布资产

| 发布文件 | 来源 | 处理 |
| --- | --- | --- |
| `engine/portal/public/blink-logo-dark.png` | `badge-dark.png` | 裁到徽章边界并向内缩 10px（避开徽章自身的抗锯齿白边），用徽章底色补成正方形，缩到 512² |
| `engine/portal/public/blink-logo-light.png` | `badge-light.png` | 同上 |
| `engine/portal/public/favicon-dark.png` | 上面的深色方图 | 512²，烘焙圆形 alpha（4× 掩膜降采样抗锯齿） |
| `engine/portal/public/favicon-light.png` | 上面的浅色方图 | 同上 |
| `engine/docs/images/banner-on-dark.webp` | `wordmark-dark.png` | 缩到 1280 宽，WebP q90 |
| `engine/docs/images/banner-on-light.webp` | `wordmark-light.png` | 同上 |

## 几条不能踩的约束

- **方形 logo 必须满幅**：portal 把它渲染成 24px 圆形（`rounded-full` + `object-cover`），带白画布会在圆里出现白环。母版本身是带画布的，所以派生时必须裁。
- **圆形必须烘进 PNG**：GitHub 会剥掉 README HTML 里的 inline style，浏览器也不会自己把 favicon 切圆。
- **favicon 保持 PNG**：浏览器对 WebP favicon 支持不一致。
- **banner 用 WebP**：平涂 + 渐变的构图 PNG 压不动（351 KB），WebP q90 只要 11.5 KB，且字标边缘无伪影。含小字的 UI 截图则相反，应保持 PNG。
- 浅色徽章与画布只差 2 级灰度，靠亮度阈值找边界会误判成熊；派生时用的是贴近底色的阈值，底色从徽章左边缘中点取（圆角处取不到）。

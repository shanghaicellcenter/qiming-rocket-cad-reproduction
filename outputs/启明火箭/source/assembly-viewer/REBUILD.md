# 整箭源装配检视页重建

已经验图的成品是 `../../整箭原件检视.html`，229,834,863 字节。归档只移动了该文件；移动前后 SHA256 均为 `f4a63caea43a70cfc97ebe248f07dc00e4fff5d1a840a54bca6182da82629a78`。本次没有重新打包或覆盖这个成品。

本目录包含中文检视源码、原件身份元数据准备器和单文件打包器。`source/viewer.js` 使用同一交付包中 `../vendor/machine` 的 Machine kit；三维引擎使用 Three.js 0.170.0，打包使用 esbuild 0.27.7。

在本目录执行：

```sh
npm install
npm run validate
npm run build
```

默认构建结果另存为 `../../整箭原件检视-rebuilt.html`。已验图的成品仍保留。需要其他位置时，可以显式指定：

```sh
node build.mjs --output ../../自定义检视页.html
```

如果本机已有这两个固定版本，可以直接指向已有 `node_modules`，无需在此安装：

```sh
MACHINE_NODE_MODULES=/absolute/path/to/node_modules node build.mjs --validate
```

`--validate` 会实际运行元数据准备器，并以内存输出编译整个浏览器 bundle（esbuild `write:false`）；它不写任何大型 HTML。结果记录在 `rebuild-validation.json`。本次实际使用已有本地依赖完成此核对，没有安装软件或联网。

`prepare_data.py` 默认从交付包 `../../native-cad` 读取15份已保存的来源元数据。可以用 `MACHINE_METADATA_BASE` 指向另一套相同结构的元数据。三份真实几何输入在 `assets.json` 中：两份整箭 GLB 位于 `../../assembly`；独立原件库位于 `../../library/supplements`。缺少任一配置输入时，构建会报错。

输出 HTML 直接嵌入三份 GLB、元数据、Machine 和 Three.js，可用 `file://` 离线打开。开发版可用 `node build.mjs --dev` 输出到当前目录，然后通过本地静态服务访问 `viewer-dev.html?dev=1`；开发版通过相对路径读取 GLB。

源 SolidWorks 到 USD/GLB 的过程包含 CAD 曲面三角化，不能称数学无损。页面保留转换文件的几何、源层级、实例与各自变换；两种显示级别来自不同三角化级别。页面不恢复 SolidWorks 的原生配合约束，也不验证制造、实物组装、工作或飞行能力。回收 MassVolume 是原项目占位几何。

研究与验图记录见 `../../research/browser-review`，此目录中的 `review` 链接保留实现者的原检查记录。来源与许可见 `THIRD-PARTY-NOTICES.md`。


## 从部件条目直接定位

主页面支持 `?part=` 后接URL编码的精确原始SLDPRT/SLDASM文件名。模型读完后会隔离并放大对应源节点；未知文件名保留整箭。显示名替换不改变内部原文件身份。该功能以活塞、翼支架总成及未知项三个实际离线状态检查，零外网请求、零脚本错误，见 `../../research/component-link-review/review.json`。

# 图卡可编辑发布源

这里保留62份真实Blender场景：17张原料示意、22张手册细节、15张功能示意和8张来源图卡。数量指场景来源记录，不是62件新增实体零件。主原生CAD、整箭装配网格及其坐标未在此转换中修改；示意图保留原先的简化程度，不构成新的制造或运行指导。

发布副本用Blender5.2.2 LTS将每个FONT对象按原场景求值转为网格轮廓，保持原有字形、布局、材质、照明与相机；已移除未使用的Apple Heiti字体软件及其packed数据。原始伙伴Blend未改。文字轮廓可作为几何编辑；原文和文字排版参数同时保存在对象自定义字段和source-parameters/{family}/{ID}.json，重新排字需采用自己有许可的字体。不得从本包推断已获Apple字体软件再分发权。

stock/、manual/、function/、source/为对应场景。font-safe-manifest.json逐项保存原始与发布SHA256、实际字体轮廓网格身份、非文字几何/UV/变换与图片溯源。fresh-reopen-audit.json为独立新进程实际重开全部62份后的检查。原始base mesh、UV与矩阵逐位相同；求值位置/拓扑/材质索引逐位相同。唯一显示容差是已在不改源的render-only control复现的Bevel临时UV浮点舍入，逐值上限2.5e-7，详情见review控制报告；未修改原modifier。

21张实际图片输入通过包内相对路径引用：19张映射source/original-project的原392快照，另2张映射既有原件预览，不复制像素改图。所有依赖的图片都在完整视觉Release中，单独拷走一个Blend文件不会同时带走相对路径图片，应保留完整目录结构。原始输入SHA与重开实际解码尺寸均有记录。

source-scripts/保留实际生成脚本、原文布局/源行参数、当前来源清单及publication-adapter。历史脚本可能保留原生产路径，不是自动执行的安装器；source-preservation.json区分原库存SHA与本次复制SHA。source8补图清单/脚本在伙伴打包图片后有更新，真实差异单独保留；不借此改写冻结的源Blend身份。发布副本可直接用包内图片和场景渲染，不依赖ni/或原桌面目录。

review/仅为发布转换前后配对渲染和数值控制证据，不作为新原设计。来源及许可遵循项目根LICENSES.md；本文件不为任何字体软件添加许可。

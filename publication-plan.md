# 公开发布与恢复准备

当前仅本地准备。工具不含创建仓库、推送、创建Release、上传或删除动作。建议公开仓库 `shanghaicellcenter/qiming-rocket-cad-reproduction`；只读查询现名返回404，不能将其当作发布时永久可用的保证。

## 冻结后执行的本地准备

```sh
python3 work/github-publication/release_tools.py derive
python3 work/github-publication/release_tools.py inventory --final-freeze
python3 work/github-publication/release_tools.py stage
python3 work/github-publication/release_tools.py pack --part-mib 512
```

所有新文件仅写在 `work/github-publication`。前两步对当前原文件做逐文件SHA256快照；后两步拒绝打包与该快照不符的文件。图册/影片/QA全部冻结后必须重跑，而非将准备期清单称为最终冻结清单。

准备期间省略 `--final-freeze` 可生成标明prepublication的清单；pack会拒绝使用该临时清单，避免误上传未冻结的图册。最终冻结还会检查文件集合未变并逐文件再核一次输入SHA256。

`derive` 对当前已验收影片仅复制视频编码流去掉音轨，保留6051帧与烧字。另把原AAC流无重编码提取为独立音轨。交互页只清空指定音频script的payload，保持其余HTML字节；用原MP3可恢复原始HTML字节。原有交付文件不改。

`inventory` 收集 `outputs/启明火箭` 和 `outputs/virtual-assembly` 完整文件，保留原392快照并再次逐字节哈希核对，记录两个内部symlink并将其归档为可移植的相对链接。整个source/audio、音频格式文件归独立NC层；两个混合音画成品替换为已核对无声副本。元数据保留原历史来源路径，运行器改用包内相对输入。

`stage` 将小型可编辑源码与工具放入 `repo-stage`，大型二进制不入Git。源文件原本超过2MiB时仍在完整视觉Release内，并不漏掉。含MIT的Machine/Three/Scenario署名、HCR原完整许可、Breeze README证据、完整Release清单。保留生成Blender可移植重建副本所需的两个原work输入：源名映射与当前旁白稿；不会复制共享node_modules、模型权重、账号信息或共享工具安装。

`pack` 生成独立可解的512MiB目标分包，每包必须小于2GiB；不是必须拼接后才可解的二进制分卷。随包提供assets.json与SHA256SUMS；完整文件清单在Git和Release各一份。GitHub[普通Git文件限制](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)为100MiB，官方[Release说明](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)允许单附件小于2GiB、每Release最多1000附件。这里采用更小分包便于重试，不引入Git LFS计费依赖。

## 实际发布后的必要验收

Root完成全部画面/页面/来源验收后才实际创建公开repo与Release。发布时先复查repo目标、分层许可和最终清单。Git只放源文本、说明与清单；Release附件包含所有模型/图/原工程/QA和独立声音包，绝不直接上传混合Breeze成片/HTML。

随后从公开Release实际重新下载全部附件到新的目录，不能把本地待上传副本当作下载验证。`verify_release.py` 对下载附件、展开文件、392源快照分别核对，再由 `restore_local.py` 在新的本地目录恢复完整声音/画面。必须记录公开URL、tag、commit、附件API大小/摘要及本地下载SHA256。

技术检查之外，实际从下载后的文件打开整箭页、全图册、无声交互页；对615或最终冻结数量的图片逐个decode，检查选择/隔离/源隐藏件与离线行为。恢复有声页实际播放/拖动/换章、核对声音时钟、字幕与几何；播放恢复MP4并核查6051帧及关键画面。打开下载的Blend做一次保存前只读检查，再决定是否需要重建测试。若依赖安装/原生CAD reader/模型权重并未随包，则清楚区分直接浏览编辑、前端重建、Blender动画重建、原CAD再转换和TTS重新生成五级能力。

## 清理边界（本工具没有删除功能）

仅在公开附件实际下载、完整恢复和浏览/播放均验收后，才由Root对“本地生成副本”逐项清理。桌面原输入、原ZIP/资料、共用skills、node/Blender/模型运行时、其他聊天工作目录、OpenDesign仍在引用的资源全部保留。需要先记录引用关系、活进程/打开文件、可恢复公开URL与哈希，生成明确删除候选清单；对symlink仅处理链接本身，不能沿链接删共用目标。用户授权清理并不等同于可删除任何同名资产。

当前所有清单是准备期快照。没有完成真实发布/下载/恢复之前，不称“已归档可删”。

## 新原料示意的字体冻结条件

实际库存为62份图卡Blend（17原料、22手册、15功能、8来源），伙伴原件含packed Apple Heiti字体，未直接进入公开包。发布副本已将554个FONT对象转为原场景实际求值网格轮廓，清除未使用的受限vfont；全部62份由独立新Blender进程实际重开，包内相对图片路径、源图片SHA及像素解码通过。原文、布局参数与真实生成脚本同时保留，原始/发布SHA逐项区分。未修改主原生CAD或392源快照。

62份转换及五组前后画面对照已完成，174文件发布源树已纳入本地交付。五组中三组逐像素相同，两组仅有极少渲染差异，数值原样记录。非文字base mesh、UV与矩阵逐位核对；临时Bevel求值UV的微小浮点差及额外七对象控制报告保留实际界限，不把历史仅哈希记录伪称已存数值数组。206图册及STEP来源入口完成真实点击复核后，由Root宣布新冻结，再执行完整清单、分包与逐包字节校验。旧冻结只作为历史，不用于新版本发布。

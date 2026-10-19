# 许可分层与署名

| 范围 | 来源及原文证据 | 发布处理 |
|---|---|---|
| 原工程392文件、CAD、派生几何/模型/图册/视觉及相应修改源码 | Half Cat Rocketry，原文件 `LICENSE-Half-Cat.txt`；原文允许GPL3或更新版，并要求发布衍生工作署名Half Cat Rocketry、按GPL3自由公开 | GPL视觉层；附完整原许可、原始源文件、修改/转换记录及可编辑对应源。不附加NC限制 |
| Machine Skill kit及其脚本 | Air Supply Technologies Inc. (Airsup)，2026，MIT；`source/vendor/machine/LICENSE` | 保留MIT文字、原署名与修改说明；本次页面派生工程并不将原库改授其他许可 |
| Three.js0.170.0 | Three.js authors，MIT；`source/vendor/machine/THREE-LICENSE.txt` | 原许可随源码、嵌入bundle与视觉包保留 |
| Blender动画bx_anim helper | Scenario Inc.，2026，MIT；`rebuild/vendor/scenario/LICENSE` | 只复制实际需要的helper与许可，不复制共享工具安装或用户配置 |
| Breeze软件源码 | 官方既有repo的Apache2.0 `LICENSE` | 仅软件代码许可；不据此声称模型/输出可商用 |
| Breeze2原始/处理WAV、MP3、精确AAC音轨及其模型相关输出 | 官方README第12、182–190行：模型、衍生模型、自托管输出仅研究/非商业；原README及SHA256见独立声音包的license-evidence | 独立NC声音层，保留声音来源、实际生成/ASR/均衡记录；不混入GPL视觉文件，也不改授MIT/GPL |
| 已同步的Breeze有声MP4、嵌入Breeze音频的HTML | 同时包含上述不同授权范围 | 不作为公开Release附件。提供本地研究/非商业恢复工具；分目录本身不能消除合成作品的许可兼容问题 |
| 17类原料的外部示意Blend中打包的Apple Heiti TC Medium字体软件 | Root已核实存在，实际全部font清单正由独立agent复开核对 | 原伙伴Blend不直接公开；只接受已评估文字轮廓/mesh且移除受限packed vfont的发布副本，或明确OFL字体替换版。PNG中的已渲染文字可保留；不声称Apple字体软件获得MIT/GPL授权 |

原Half Cat文本同时写有“GPLv3或更新版”和额外的“GPL version3”归属要求，因此保留完整文本，不用一个简化SPDX标签取代原文。对原作者与原项目名称的来源标识不因中文展示名改变。

仓库与Release是带各自授权边界的独立作品聚合；没有用一个总许可限制接收者对独立GPL视觉的权利。GNU的[聚合与合并说明](https://www.gnu.org/licenses/gpl-faq.en.html#MereAggregation)及[GPLv3第5节](https://www.gnu.org/licenses/gpl-3.0.html#section5)区分独立聚合与衍生组合；本安排不把“分成两个压缩包”当作对已经同步成片的兼容性裁定。

Breeze原文来源：[官方repo](https://github.com/breezeblue-ai/breeze-tts)，README指向[模型许可](https://huggingface.co/BreezeBlue/Breeze-TTS-2/blob/main/LICENSE)。这里依据本项目已经使用的现有本地repo文本记录授权范围，没有取得额外商业授权，也没有调用付费平台。

字体处理仅针对新增示意资产的发布副本；主原生CAD/Blend几何与伙伴原Blend均不改。轮廓副本仍保留几何/布局编辑能力，原文参数与脚本另附；文字重新排版需使用另有明确许可的开放字体。最终冻结前必须把实际font清单、去包后复开检查与发布副本SHA256纳入证据，不能把改名或清空filepath当作已移除打包字体。

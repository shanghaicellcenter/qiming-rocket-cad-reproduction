# 启明火箭 · 逐步虚拟归位讲解源码

此页使用同一份真实源CAD浏览几何，不增加内部部件。展示副本共享几何；15组互斥覆盖688个源网格，原参考层级不参与展示动画。

`source/film.js` 是取景、显示与声音控制，`source/data.js` 保存逐段讲稿、来源、15组源路径、最终语音时码。`silent-timeline.json` 记录录制基础章节；`final-timeline.json` 记录按真实旁白时长调整后的时间。字幕时间来自实际语音识别和核对，不按字数推算。

重建离线交互页：在本目录安装 package.json 固定版本依赖，再执行 `node build.mjs`。也可以将 MACHINE_NODE_MODULES 指向已有对应依赖目录。输入为 ../../assembly/vehicle-browse.compact.glb、../../library/assembly-previews/A12-side.png、../../media/逐步虚拟归位旁白.mp3。输出为 ../../逐步虚拟归位.html，模型、图片、声音和代码全部内嵌，不依赖联网。

影片重渲：安装上述依赖、可用Chromium或Google Chrome及ffmpeg/ffprobe，再执行 `python3 render_movie.py`。脚本按真实最终时码逐章录制，可从已验证章节继续，默认写一个 rebuilt 副本，保留已验收原片。MACHINE_NODE、MACHINE_PLAYWRIGHT_MODULE、MACHINE_CHROMIUM_EXECUTABLE可指定已有运行时；不会调用TTS，也不会重新均衡或加速声音。重渲是重新取样与编码，不承诺MP4字节完全相同。

旁白使用用户确认方向的Spark本地合成声，每段一次生成；均衡音量保留采样数和实际时码。播放以真实音频时钟为准，拖动和章节选择同时定位音画。源WAV、字幕与核查记录另附，不代表合成模型运行环境已经打包。

影片通过相同展示代码录制各章，再按实际语音时长调整画面，隔套、四侧尾翼、连接环和辅助塞的近景按实测词句时间定位；声音不加速。MP4字幕烧录，另附SRT。Blender可编辑源与坐标检查放在 ../../../virtual-assembly/。

Machine Skill源代码许可与修改说明见 ../vendor/machine/。Three.js许可见 ../vendor/machine/THREE-LICENSE.txt。原工程及派生CAD归属Half Cat Rocketry。

# StudyFlow 题包制作

把试卷、截图和参考答案整理成可导入 StudyFlow 的整套练习。支持六科的单选、多选、判断、填空，以及英语阅读材料和编号空位。

## 在豆包工作中从 GitHub 安装

把下面这句话发给豆包工作，按它提示确认安装。

> 请为我安装这个 GitHub 仓库里的 StudyFlow 题包制作 Skill：https://github.com/pbbtwxsqhdxqhdw/studyflow-skill

安装后，上传试卷和参考答案，再说「生成 StudyFlow 题包」。

## 在豆包普通聊天里使用

1. 打开 [题包制作指令](doubao-prompt.md)，复制正文到豆包。
2. 上传试卷和参考答案，请豆包按指令生成题包。
3. 如果当前聊天只能输出文字，请它完整输出清单。纯文字题包可将清单保存为 UTF-8 的 `.json` 文件，再导入 StudyFlow。含图片的题包需要把原图文件和清单一起打包。

在 StudyFlow 打开「练习库 → 导入整套练习」，上传生成的 ZIP 或 JSON 后核对预览。

## 下载 Skill

[下载 Skill ZIP](studyflow-question-pack.zip) · [查看 Skill 源文件](SKILL.md)

在支持上传 Agent Skill 的工具中使用这个 ZIP。压缩包内包含指令、题包格式和打包检查脚本。Skill ZIP 用于安装。运行后生成的题包 ZIP 用于导入 StudyFlow。

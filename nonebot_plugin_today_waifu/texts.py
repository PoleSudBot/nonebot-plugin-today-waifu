from __future__ import annotations

import random

from .constants import DIVORCE_EXHAUSTED_TEXT, NO_WAIFU_TEXT, PURE_LOVE_ONLY_TEXT

HELP_TEXT = """
💍 基础玩法
- 今日老婆：抽今天的群友老婆，同一天返回同一位
- 换老婆：默认模式可用，按本群设置消耗次数
- 离婚/分手：清空今日关系并耗尽今天次数
- 老婆设置：查看本群抽取设置与当前生效主题

🎨 主题设置
- 老婆主题列表：查看主题序号，当前支持 BangDream / PJSK 等
- 查看老婆主题：查看各层级主题与当前生效结果
- (群|全局)老婆主题设置 <序号>：设置对应级别主题，支持all/none，多选用逗号分隔
- 重置(群|全局)老婆主题：清除覆盖，恢复默认设置

⚙️ 群配置 (群管/超管)
- 纯爱模式 <开启/关闭>：开启次日生效，关闭立即生效，也支持 on/off
- 换老婆 <开启/关闭>：控制本群是否允许换老婆，也支持 on/off
- 设置换老婆次数 <N>：设置每天最多可换次数
- 设置抽取模式 <随机/活跃>：配置抽取逻辑为随机或基于近期活跃度
- 设置活跃天数 <N>：活跃模式优先抽取最近 N 天发言群友

📰 刊物与统计
- 本群cp/花名册：查看今日当前所有实时配对
- 缘分(周/月/年)刊：手动查看本群数据总结
- 缘分周刊 <开启/关闭>：管理本群刊物自动推送订阅，也支持 on/off
- [本群]里程碑提醒 <开启/关闭>：管理结缘里程碑提醒，也支持 on/off
""".strip()


def first_pick_text(is_bot: bool) -> str:
    if is_bot:
        return random.choice([
            "你今天的群友老婆是我哦~",
            "锵锵！今天由我来做你的老婆，请多指教呀~",
            "命中注定就是我啦！今天本姬就是你的专属老婆~",
            "找半天没有合适的人选呢……那就勉为其难由我来做你的老婆吧！"
        ])
    return random.choice([
        "你今天的群友老婆是：",
        "为你牵线成功！今天的缘分属于：",
        "漫长的等待只为这一刻，你今天的老婆是：",
        "经过一番奇妙的红娘计算，你今天的专属老婆是："
    ])


def repeat_pick_text(is_bot: bool) -> str:
    if is_bot:
        return random.choice([
            "你今天已经有老婆了，是我哦，不可以再有别人了呢~",
            "盯着我一个人看不好嘛？今天你已经绑定我啦，不可以再看别人哦~",
            "怎么还在找老婆呀，看看你身边，今天我才是你的专属哦~"
        ])
    return random.choice([
        "你今天已经有老婆了，要好好对待她哦~",
        "花心可不好，请全心全意对待你今天的老婆吧！",
        "你们今天已经锁死啦，快去和老婆贴贴吧！"
    ])


def mirror_first_pick_text(is_bot: bool) -> str:
    if is_bot:
        return random.choice([
            "命运替你做了决定，你今天的群友老婆是我哦~",
            "是命中注定的缘分呢，今天我做你的老婆~",
            "哎呀，这就叫天注定吗？总之今天本姬就是你的老婆啦！"
        ])
    return random.choice([
        "命运替你做了决定，你今天的群友老婆是：",
        "在命运红线的牵引下，你今天的老婆是：",
        "缘，妙不可言~ 被命运选中的ta是："
    ])


def change_success_text(is_bot: bool, remaining: int | None) -> str:
    if remaining == 0:
        if is_bot:
            return random.choice([
                "渣男，再换你今天就没老婆了！\n你今天的群友老婆是我哦~",
                "这是最后一次机会了哦！再换就只能孤寡一天了！\n没办法，暂时勉为其难做你的老婆吧~"
            ])
        return random.choice([
            "渣男，再换你今天就没老婆了！\n你今天的群友老婆是：",
            "换得挺爽？这可是最后一次了！\n你今天的新老婆是："
        ])
    if is_bot:
        return random.choice([
            "你今天的群友老婆是我哦~\n如果你这个大猪蹄子敢抛弃我的话，你今天就没老婆了哦",
            "换了一圈竟然遇到我了！\n再敢换掉我的话，今天就准备一个人对着墙角哭去吧！"
        ])
    return random.choice([
        "你今天的群友老婆是：",
        "变心成功！你今天的新老婆是：",
        "见异思迁的家伙……那么，你现在的老婆是："
    ])


def pure_love_block_change_text() -> str:
    return random.choice([
        "纯爱模式下不能换老婆，收收心吧。",
        "纯爱战神不斩旧爱，今天请对现在的ta始终如一！",
        "既然选择了，就不要想着换啦，纯爱模式下可不支持花心哦~"
    ])


def change_disabled_text() -> str:
    return random.choice([
        "本群已经关闭换老婆了，今天就老老实实专一一点。",
        "换老婆功能休息中，今天请安静地做个纯爱党~",
        "不满足也没办法，既然关了换老婆，就好好对待这份缘分吧！"
    ])


def need_pick_first_text() -> str:
    return random.choice([
        "换老婆前请先娶个老婆哦，渣男",
        "你连老婆都没有，在这里换给谁看呀？快去领一个！",
        "想凭空换老婆？先去结缘再来说话吧！"
    ])


def no_waifu_text() -> str:
    return NO_WAIFU_TEXT


def divorce_text() -> str:
    return DIVORCE_EXHAUSTED_TEXT


def pure_love_only_text() -> str:
    return PURE_LOVE_ONLY_TEXT


def mutual_love_text() -> str:
    return random.choice([
        "你们今天是双向奔赴，民政局直接给你们把门焊死了。",
        "哎呀呀，竟然是双向奔赴的纯爱！快去办个婚礼吧！",
        "两情相悦！太甜了太甜了，祝福你们！"
    ])


def special_role_text(role_tag: str) -> str | None:
    mapping = {
        "SUPERUSER": random.choice([
            "咦，怎么是机主大人……感觉气氛变得微妙起来了。",
            "哇哦，居然和开发者绑定了，不知为何有些敬畏呢。",
            "天哪，今天的结缘对象可是这只机器人的主人，说话要小心咯！"
        ]),
        "OWNER": random.choice([
            "今天群主是你的老婆！这算是抱上大腿了吗？",
            "居然和群主凑成一对了，今天这缘分深不可测呀。",
            "原来今天群主负责查岗……啊不，是陪你！"
        ]),
        "ADMINISTRATOR": random.choice([
            "和管理员结缘了，看来你今天的面子很大呢。",
            "今天和管理员绑在一起了，敢调皮的话当心被关小黑屋哦。",
            "管理员大人今天居然归你了，可要好好照顾他呀。"
        ]),
    }
    return mapping.get(role_tag)


def milestone_text(count: int, self_name: str, target_name: str) -> str:
    if count == 10:
        return random.choice([
            f"恭喜 {self_name} 和 {target_name} 累计结缘 10 次，已经开始让人怀疑是不是锁死了。",
            f"十全十美！{self_name} 与 {target_name} 已经撞上 10 次姻缘了，是不是该发喜糖了？"
        ])
    if count == 50:
        return random.choice([
            f"{self_name} 对 {target_name} 已经累计 50 次，这份执念多少有点吓人了。",
            f"半百之缘！{self_name} 与 {target_name} 这是什么神仙眷侣，请原地结婚好吗！"
        ])
    if count == 100:
        return random.choice([
            f"{self_name} 和 {target_name} 的累计缘分冲到 100 次，建议直接去领证。",
            f"简直是奇迹！{self_name} 和 {target_name} 结缘已经满 100 次了，百年好合！"
        ])
    candidates = [
        f"{self_name} 和 {target_name} 的累计缘分来到 {count} 次，恭喜恭喜。",
        f"命运的齿轮再次转动，{self_name} 和 {target_name} 已经结缘了 {count} 次！",
        f"真是有缘千里来相会，这是 {self_name} 与 {target_name} 第 {count} 次成为限定CP了哦~",
        f"怎么又是你们俩！{self_name} 和 {target_name} 的缘分值已经涨到 {count} 了！",
        f"这绝对存在某种暗箱操作吧？{self_name} 与 {target_name} 结缘次数居然高达 {count} 次了！"
    ]
    return random.choice(candidates)

from __future__ import annotations

import random

from .constants import DIVORCE_EXHAUSTED_TEXT, NO_WAIFU_TEXT, PURE_LOVE_ONLY_TEXT

HELP_TEXT = """
💍 基础玩法
- 今日老婆：抽今天的群友老婆，同一天返回同一位
- 换老婆：默认模式可用，按本群设置消耗次数
- 离婚/分手：主动解除今日关系，并暂时退出当天待选池
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
            "诶？今天抽到我了吗？那、那个……今天就由我来做你的老婆，我会努力的！",
            "锵锵！今天是我哦！请、请多指教呀~",
            "哇，是我呢！今天一整天，就让我做你的专属老婆吧，嘿嘿~",
            "那个……找不到其他人的话，我来陪着你吧！今天我也会为你加油的哦！"
        ])
    return random.choice([
        "心意传达！你今天的群友老婆是：",
        "希望这份缘分能好好传达呢！你今天的老婆是：",
        "为你找到啦！你今天的专属老婆是：",
        "哇，红线牵在一起了呢！你今天的老婆是："
    ])


def repeat_pick_text(is_bot: bool) -> str:
    if is_bot:
        return random.choice([
            "诶诶？今天明明已经有我了呀，要好好看着我才行哦！",
            "那个……今天我的专属位置是不可以换人的哦！",
            "还、还在找吗？今天有我陪着你，不可以再看别人啦！"
        ])
    return random.choice([
        "你今天已经有老婆啦，要好好珍惜这份缘分哦！",
        "太花心的话可是不行的，请全心全意对待你今天的老婆吧！",
        "今天已经绑定啦！快去和老婆好好相处吧，我也会为你们加油的！"
    ])


def mirror_first_pick_text(is_bot: bool) -> str:
    if is_bot:
        return random.choice([
            "好像是命运的安排呢！今天我是你的群友老婆哦~",
            "既然是命中注定的缘分，今天就请多多指教啦！",
            "诶嘿嘿，这就是奇妙的缘分吗？总之今天我就是你的老婆啦！"
        ])
    return random.choice([
        "好像是命运的安排呢！你今天的群友老婆是：",
        "顺着命运的红线找过去，你今天的老婆是：",
        "这就是奇妙的缘分呀~ 被命运选中的人是："
    ])


def change_success_text(is_bot: bool, remaining: int | None) -> str:
    if remaining == 0:
        if is_bot:
            return random.choice([
                "真是的，太花心了啦！这可是最后一次机会了哦！\n今天就由我来陪你吧，不可以再换了！",
                "再换的话今天可就要孤零零一个人了哦！\n没办法，最后就让我来做你的老婆吧~"
            ])
        return random.choice([
            "真是的，太花心了啦！这可是最后一次机会了哦，再换的话今天就要孤单一个人了！\n你今天的新老婆是：",
            "换了这么多次……要好好珍惜最后一次机会呀！\n你今天的新老婆是："
        ])
    if is_bot:
        return random.choice([
            "诶？换了一圈居然遇到我了！\n那、那个，如果再把我换掉的话，我可是会很伤心的哦！",
            "今天的新老婆是我哦！\n不可以再换了，要好好看着我呀！"
        ])
    return random.choice([
        "心意更新！你今天的新老婆是：",
        "既然换了，这次一定要好好珍惜呀！你现在的老婆是：",
        "哇，缘分又发生了变化呢……你今天的新老婆是："
    ])


def pure_love_block_change_text() -> str:
    return random.choice([
        "现在是纯爱模式，不可以换老婆的哦。要始终如一呀！",
        "纯爱可是很珍贵的，今天请对现在的ta全心全意吧！",
        "既然已经选定了，就不要想着换啦，纯爱模式下可不允许花心哦！"
    ])


def change_disabled_text() -> str:
    return random.choice([
        "本群已经关闭换老婆的功能啦，今天就老老实实专一一点吧~",
        "换老婆功能休息中哦！今天请好好珍惜最初的缘分吧！",
        "不可以换老婆啦，既然已经决定了，就要好好对待人家哦！"
    ])


def need_pick_first_text() -> str:
    return random.choice([
        "诶？可是你还没有老婆呀，要先去结缘才能换哦！",
        "连老婆都没有就想着换，这样可不行呢！快去抽一个吧！",
        "想凭空换老婆是不可能的啦，先去寻找今天的缘分吧！"
    ])


def no_waifu_text() -> str:
    return NO_WAIFU_TEXT


def no_available_waifu_text() -> str:
    return random.choice([
        "今天暂时没有可结缘对象，晚点再试试吧。",
        "现在候选池空空的，今天先休息一下也不错。",
        "暂时找不到可以结缘的人选，等群里热闹一点再来吧。",
    ])


def pure_love_pick_busy_text() -> str:
    return random.choice([
        "现在结缘请求有点密集，请稍后再试一次。",
        "红线刚刚打了个结，等一下再抽会更稳。",
        "当前纯爱配对正在更新中，请稍后再试。",
    ])


def member_query_unavailable_text() -> str:
    return "当前无法获取群成员列表，暂时不能抽取今日老婆。"


def divorce_success_text() -> str:
    return random.choice([
        "今日关系已解除。今天你会暂时退出待选池，明天再重新开始吧。",
        "已经为你结束今天的关系。今天不会再把你放进待选池，明天再重新结缘吧。",
        "分开也需要好好收尾。今天你会暂时退出待选池，明天再重新开始。",
    ])


def need_divorce_pick_first_text() -> str:
    return random.choice([
        "你今天还没有结缘，不能离婚/分手。先去抽一个老婆吧。",
        "还没有今日关系可以解除哦，先结缘之后才能分开。",
        "现在没有可离的关系。要先抽到老婆，才谈得上离婚/分手。",
    ])


def already_divorced_text() -> str:
    return random.choice([
        "你今天已经解除过关系了，明天再重新开始吧。",
        "今天的关系已经收尾啦，不用重复离婚/分手。",
        "今日已退出待选池，等明天再重新结缘吧。",
    ])


def no_divorce_target_text() -> str:
    return random.choice([
        "你现在没有可解除的今日关系。",
        "今天已经没有老婆可以分开了。",
        "当前没有可离的关系，先等明天重新开始吧。",
    ])


def divorce_text() -> str:
    return DIVORCE_EXHAUSTED_TEXT


def pure_love_only_text() -> str:
    return PURE_LOVE_ONLY_TEXT


def mutual_love_text() -> str:
    return random.choice([
        "哇！你们今天是双向奔赴呢，这一定是奇迹吧，太棒了！",
        "诶呀呀，居然是双向的纯爱！太让人感动了，祝福你们哦！",
        "两情相悦！太甜了太甜了，我也会为你们应援的！"
    ])


def milestone_text(count: int, self_name: str, target_name: str) -> str:
    if count == 10:
        return random.choice([
            f"恭喜 {self_name} 和 {target_name} 已经结缘 10 次啦！你们的感情真的很好呢！",
            f"哇，十全十美！{self_name} 和 {target_name} 已经相遇 10 次了，真是太有默契啦！"
        ])
    if count == 50:
        return random.choice([
            f"{self_name} 和 {target_name} 居然已经结缘 50 次了！这份心意一定好好传达到了吧！",
            f"半百的缘分！{self_name} 和 {target_name} 感情太好啦，真让人羡慕呢！"
        ])
    if count == 100:
        return random.choice([
            f"天哪，100 次！{self_name} 和 {target_name} 的缘分真的创造奇迹了！祝你们百年好合！",
            f"简直像做梦一样！{self_name} 和 {target_name} 结缘已经满 100 次了，一定要永远幸福哦！"
        ])
    candidates =[
        f"命运的齿轮再次转动，{self_name} 和 {target_name} 已经结缘了 {count} 次啦！",
        f"{self_name} 和 {target_name} 的累计缘分来到了 {count} 次，恭喜你们！",
        f"真是有缘呢，这是 {self_name} 和 {target_name} 第 {count} 次结缘了哦~",
        f"哇，又是你们俩！{self_name} 和 {target_name} 的缘分值已经涨到 {count} 啦！",
        f"太厉害了！{self_name} 和 {target_name} 结缘次数居然已经有 {count} 次了，要继续保持哦！"
    ]
    return random.choice(candidates)

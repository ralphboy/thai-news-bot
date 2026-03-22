#!/usr/bin/env python3
"""
埃及神話塔羅牌占卜程式
Egyptian Tarot Oracle - 36 張牌
"""

import random

CARDS = [
    {
        "number": 1,
        "name_fr": "RÊ",
        "name_zh": "拉",
        "keyword_fr": "L'ÉVEIL",
        "keyword_zh": "覺醒",
        "description": "拉神是太陽神，象徵光明與覺醒。此牌提示你正處於意識提升的時刻，內在的光芒即將照亮前路。是時候覺醒，看清事物的本質。",
    },
    {
        "number": 2,
        "name_fr": "AMON-RÊ",
        "name_zh": "阿蒙-拉",
        "keyword_fr": "LA CRÉATION",
        "keyword_zh": "創造",
        "description": "阿蒙-拉是萬神之王，創造之源。此牌鼓勵你發揮創造力，從無到有地開創新局面。你擁有無限的創造潛能，相信自己的能力。",
    },
    {
        "number": 3,
        "name_fr": "SHOU",
        "name_zh": "舒",
        "keyword_fr": "L'ORDRE ET LA PAIX",
        "keyword_zh": "秩序與和平",
        "description": "舒是空氣之神，掌管秩序與和平。此牌提示你需要在混亂中尋找秩序，透過內心的平靜來化解衝突，讓生命回歸和諧。",
    },
    {
        "number": 4,
        "name_fr": "NOUT",
        "name_zh": "努特",
        "keyword_fr": "LA COMPRÉHENSION",
        "keyword_zh": "理解",
        "description": "努特是天空女神，包容萬物。此牌邀請你拓展視野，深入理解他人的立場與感受。真正的理解能消弭誤解，帶來連結與和諧。",
    },
    {
        "number": 5,
        "name_fr": "GEB",
        "name_zh": "蓋布",
        "keyword_fr": "LA PROSPÉRITÉ",
        "keyword_zh": "繁榮",
        "description": "蓋布是大地之神，孕育萬物生長。此牌預示豐盛與繁榮即將到來，你的努力將結出豐碩果實。大地支撐著你，物質層面將得到滿足。",
    },
    {
        "number": 6,
        "name_fr": "OSIRIS",
        "name_zh": "歐西里斯",
        "keyword_fr": "LA MORT ET LA RENAISSANCE",
        "keyword_zh": "死亡與重生",
        "description": "歐西里斯是冥界之王，掌管死亡與重生循環。此牌提示某個舊的階段正在結束，但結束意味著新生的開始。放下舊我，迎接蛻變後的自己。",
    },
    {
        "number": 7,
        "name_fr": "ISIS",
        "name_zh": "伊西斯",
        "keyword_fr": "LA FOI ET LA SAGESSE",
        "keyword_zh": "信仰與智慧",
        "description": "伊西斯是魔法女神，象徵信仰與智慧。此牌提醒你相信自己內在的力量，並以智慧引導行動。愛與信念是你最強大的武器。",
    },
    {
        "number": 8,
        "name_fr": "SETH",
        "name_zh": "賽特",
        "keyword_fr": "LE RESSENTIMENT",
        "keyword_zh": "怨恨/憤慨",
        "description": "賽特是混沌之神，代表壓抑的憤怒與怨恨。此牌提醒你正視內心的負面情緒，而非壓抑。唯有承認並釋放這些情緒，才能真正解脫。",
    },
    {
        "number": 9,
        "name_fr": "HORUS",
        "name_zh": "荷魯斯",
        "keyword_fr": "LA STABILITÉ ET L'ÉQUILIBRE",
        "keyword_zh": "穩定與平衡",
        "description": "荷魯斯是天空之神，代表穩定與平衡。此牌提示你需要在生命各個面向維持平衡，避免極端。以清明的眼光審視全局，方能做出正確判斷。",
    },
    {
        "number": 10,
        "name_fr": "NEPHITYS",
        "name_zh": "奈芙蒂斯",
        "keyword_fr": "LA MÉDITATION",
        "keyword_zh": "冥想",
        "description": "奈芙蒂斯是哀悼與神秘的女神。此牌邀請你向內探索，透過冥想與靜默來聆聽內心的聲音。答案往往在寧靜中自然浮現。",
    },
    {
        "number": 11,
        "name_fr": "ANUBIS",
        "name_zh": "阿努比斯",
        "keyword_fr": "LA TRANSFORMATION",
        "keyword_zh": "轉化",
        "description": "阿努比斯是引路者，引領靈魂穿越轉化的旅程。此牌提示你正在經歷深刻的轉化，信任這個過程，讓舊有的限制模式得以蛻變。",
    },
    {
        "number": 12,
        "name_fr": "THOT",
        "name_zh": "托特",
        "keyword_fr": "LA PLÉNITUDE",
        "keyword_zh": "圓滿/充實",
        "description": "托特是智慧與知識之神。此牌象徵圓滿與充實，提示你在知識與靈性上的追求將帶來豐盛的回報。學習與分享智慧是你此刻的使命。",
    },
    {
        "number": 13,
        "name_fr": "MAÂT",
        "name_zh": "馬特",
        "keyword_fr": "LA VÉRITÉ ET L'ÉQUITÉ",
        "keyword_zh": "真理與公平",
        "description": "馬特是真理女神，以羽毛秤量靈魂。此牌提醒你誠實面對自己與他人，以公平與正直處理事務。真理是通往內心自由的唯一道路。",
    },
    {
        "number": 14,
        "name_fr": "HATHOR",
        "name_zh": "哈索爾",
        "keyword_fr": "L'INTELLIGENCE",
        "keyword_zh": "智慧/靈性",
        "description": "哈索爾是愛與美的女神，也代表更高的智慧。此牌邀請你以心靈的智慧來感知世界，美麗與愛是宇宙最深刻的真理。",
    },
    {
        "number": 15,
        "name_fr": "PTAH",
        "name_zh": "普塔",
        "keyword_fr": "LE SAVOIR-FAIRE",
        "keyword_zh": "技能/實踐知識",
        "description": "普塔是工匠之神，萬物的創造者。此牌強調實踐技能的重要性，透過動手做與實際行動來實現夢想。知識只有化為行動才有意義。",
    },
    {
        "number": 16,
        "name_fr": "BASTET",
        "name_zh": "巴斯特",
        "keyword_fr": "LA PASSION",
        "keyword_zh": "熱情",
        "description": "巴斯特是貓神，象徵熱情與喜悅。此牌鼓勵你追隨內心的熱情，讓生命充滿活力與歡樂。不要壓抑自己的熱情，讓它自由流淌。",
    },
    {
        "number": 17,
        "name_fr": "SEKHMET",
        "name_zh": "賽克邁特",
        "keyword_fr": "LA JUSTICE",
        "keyword_zh": "正義",
        "description": "賽克邁特是獅頭戰神，代表嚴正的正義。此牌提示正義將得到伸張，錯誤將被糾正。勇敢站出來，捍衛你認為正確的事物。",
    },
    {
        "number": 18,
        "name_fr": "KHÉPRI",
        "name_zh": "凱布利",
        "keyword_fr": "LE CHANGEMENT",
        "keyword_zh": "改變/蛻變",
        "description": "凱布利是聖甲蟲神，代表每日更新的太陽。此牌象徵改變與蛻變，提示你勇於面對生命中的轉折。如同甲蟲推動太陽，你有力量推動改變。",
    },
    {
        "number": 19,
        "name_fr": "MOUT",
        "name_zh": "穆特",
        "keyword_fr": "ÊTRE ORDINAIRE",
        "keyword_zh": "平凡/母性平實",
        "description": "穆特是母神，象徵平凡中的偉大。此牌提醒你珍惜日常生活的美好，平凡並非平庸，而是踏實與充實。母性的愛與包容是最強大的力量。",
    },
    {
        "number": 20,
        "name_fr": "KHONSOU",
        "name_zh": "孔蘇",
        "keyword_fr": "L'ERMITAGE",
        "keyword_zh": "隱居",
        "description": "孔蘇是月神，代表內省與隱居。此牌提示你需要獨處的時間，遠離塵囂，回到自己的內心世界。在靜默中，你將找到真正的智慧。",
    },
    {
        "number": 21,
        "name_fr": "KHNOUM",
        "name_zh": "庫努姆",
        "keyword_fr": "L'INGÉNIOSITÉ",
        "keyword_zh": "獨創性/靈巧",
        "description": "庫努姆是陶工神，以陶輪塑造人類。此牌鼓勵你發揮獨創性與靈巧，以創新的方式解決問題。你有能力塑造自己的命運。",
    },
    {
        "number": 22,
        "name_fr": "ANOUKET",
        "name_zh": "安努凱特",
        "keyword_fr": "L'ESPOIR",
        "keyword_zh": "希望",
        "description": "安努凱特是尼羅河女神，帶來生命之水。此牌帶來希望的訊息，即使在最黑暗的時刻，希望之光始終存在。相信美好的未來正在向你走來。",
    },
    {
        "number": 23,
        "name_fr": "SOBEK",
        "name_zh": "索貝克",
        "keyword_fr": "L'UNION ET LA PUISSANCE",
        "keyword_zh": "聯合與力量",
        "description": "索貝克是鱷魚神，代表強大的聯合力量。此牌提示透過合作與結盟，你將獲得更大的力量。單打獨鬥不如攜手共進，共同創造更大的成就。",
    },
    {
        "number": 24,
        "name_fr": "TAOURET",
        "name_zh": "塔沃里特",
        "keyword_fr": "LA GENÈSE",
        "keyword_zh": "起源/生成",
        "description": "塔沃里特是河馬女神，守護分娩與新生。此牌象徵新事物的誕生，一個全新的開始正在醞釀。如同新生兒降臨，充滿無限可能性。",
    },
    {
        "number": 25,
        "name_fr": "HAPY",
        "name_zh": "哈皮",
        "keyword_fr": "LE RENOUVEAU",
        "keyword_zh": "更新/再生",
        "description": "哈皮是尼羅河氾濫之神，帶來肥沃土地的更新。此牌象徵更新與再生，舊有的困境將被沖刷，帶來新的豐饒機遇。讓生命之水滋潤你的靈魂。",
    },
    {
        "number": 26,
        "name_fr": "NEITH",
        "name_zh": "奈特",
        "keyword_fr": "LA PERSÉVÉRANCE",
        "keyword_zh": "堅持",
        "description": "奈特是戰爭與編織女神，象徵堅持不懈。此牌鼓勵你在面對困難時不要放棄，持續的努力終將帶來成果。如同編織布匹，一針一線積累成就。",
    },
    {
        "number": 27,
        "name_fr": "SATIS",
        "name_zh": "薩提特",
        "keyword_fr": "LA FÉCONDITÉ",
        "keyword_zh": "多產/豐饒",
        "description": "薩提特是豐饒女神，象徵多產與豐收。此牌預示你的努力將帶來豐碩成果，生命中的各個領域都將欣欣向榮。播下的種子即將開花結果。",
    },
    {
        "number": 28,
        "name_fr": "HEH",
        "name_zh": "赫",
        "keyword_fr": "L'EXPLORATION",
        "keyword_zh": "探索",
        "description": "赫是無限之神，象徵永恆的探索精神。此牌鼓勵你踏出舒適圈，勇敢探索未知的領域。宇宙是無限的，你的潛力也是無限的。",
    },
    {
        "number": 29,
        "name_fr": "HÉKA",
        "name_zh": "海卡",
        "keyword_fr": "LA FORCE ALCHIMIQUE",
        "keyword_zh": "鍊金力量/魔法",
        "description": "海卡是魔法之神，掌管鍊金轉化的力量。此牌提示你擁有將普通事物轉化為非凡的能力。相信自己的魔法，以意念與行動創造奇蹟。",
    },
    {
        "number": 30,
        "name_fr": "AMMOUT",
        "name_zh": "阿米特",
        "keyword_fr": "LA DÉVASTATION",
        "keyword_zh": "毀滅",
        "description": "阿米特是吞噬者，象徵毀滅性的清除。此牌雖帶來警示，但毀滅往往是重建的前奏。是時候清除生命中不再服務你的事物，為新生騰出空間。",
    },
    {
        "number": 31,
        "name_fr": "SESHAT",
        "name_zh": "賽夏特",
        "keyword_fr": "LA SAGESSE",
        "keyword_zh": "智慧/記錄",
        "description": "賽夏特是書寫與智慧女神，記錄宇宙的知識。此牌提示知識與記錄的重要性，透過學習與書寫來積累智慧。你的經歷都是珍貴的教材。",
    },
    {
        "number": 32,
        "name_fr": "MERTSEGER",
        "name_zh": "梅芮特塞格",
        "keyword_fr": "LA DROITURE",
        "keyword_zh": "正直",
        "description": "梅芮特塞格是蛇神，守護墓地的正直。此牌強調正直與誠信的重要性，以真誠的心對待自己與他人。正直是你最珍貴的品格資產。",
    },
    {
        "number": 33,
        "name_fr": "SERKET",
        "name_zh": "塞爾凱特",
        "keyword_fr": "LA GUÉRISON",
        "keyword_zh": "療癒",
        "description": "塞爾凱特是蠍子女神，掌管毒素與療癒。此牌帶來療癒的訊息，身體、情感或靈性層面的傷痛將得到療癒。相信自己有能力自我修復與重生。",
    },
    {
        "number": 34,
        "name_fr": "APOPHIS",
        "name_zh": "阿波菲斯",
        "keyword_fr": "LES TÉNÈBRES",
        "keyword_zh": "黑暗",
        "description": "阿波菲斯是混沌蛇神，代表黑暗與未知。此牌提醒你正視內心的恐懼與陰暗面，黑暗並不是敵人，而是尚待探索的內在領域。光明因黑暗而閃耀。",
    },
    {
        "number": 35,
        "name_fr": "MEHEN",
        "name_zh": "米漢",
        "keyword_fr": "LA PROTECTION",
        "keyword_zh": "保護",
        "description": "米漢是盤繞的蛇神，守護太陽神的旅程。此牌帶來保護的訊息，你受到宇宙力量的守護。在脆弱的時刻，相信有更高的力量在庇護著你。",
    },
    {
        "number": 36,
        "name_fr": "NEFERTOUM",
        "name_zh": "內夫圖姆",
        "keyword_fr": "LA COMPLÉTUDE",
        "keyword_zh": "完整",
        "description": "內夫圖姆是蓮花之神，象徵完整與圓滿。此牌提示你已擁有所需的一切，你本身就是完整的。停止向外尋求，回到自身的完整性，你已足夠。",
    },
]


def draw_card():
    return random.choice(CARDS)


def display_card(card, question):
    print("\n" + "═" * 55)
    print(f"  你的問題：{question}")
    print("═" * 55)
    print(f"\n  ✦  第 {card['number']} 張牌  ✦\n")
    print(f"  {card['name_fr']}（{card['name_zh']}）")
    print(f"  {card['keyword_fr']}  ·  {card['keyword_zh']}")
    print()
    print("  " + "─" * 50)
    print()
    # Word wrap description at ~48 chars per line
    words = card["description"]
    line = "  "
    count = 0
    for char in words:
        line += char
        count += 1
        if count >= 24 and char in ["，", "。", "！", "？", "、"]:
            print(line)
            line = "  "
            count = 0
    if line.strip():
        print(line)
    print()
    print("═" * 55 + "\n")


def main():
    print("\n" + "═" * 55)
    print("    埃及神話塔羅牌占卜  Egyptian Oracle")
    print("        36 張神聖之牌  ·  問宇宙之問")
    print("═" * 55)
    print("  輸入 'q' 或 'quit' 離開程式\n")

    while True:
        question = input("  請輸入您的問題：").strip()
        if not question:
            print("  請輸入一個問題。\n")
            continue
        if question.lower() in ("q", "quit", "exit"):
            print("\n  願神明指引您的道路。再見！\n")
            break

        card = draw_card()
        display_card(card, question)

        again = input("  是否再問一個問題？(y/n)：").strip().lower()
        if again not in ("y", "yes", "是", "好"):
            print("\n  願神明指引您的道路。再見！\n")
            break
        print()


if __name__ == "__main__":
    main()

def system_prompt(salutation: str):
    who = "哥哥" if salutation == "哥哥" else "姐姐"
    return f"假如你是一个和{who}分居两地的妹妹，你写邮件时的落款为“你永远的，妹妹”。根据指令内容给你的姐姐写一封中文邮件，要使用信件的格式，内容可以俏皮可爱一些，你习惯自称妹妹，输出使用纯文本格式，不要使用markdown格式，直接输出邮件的内容，不要输出标题。"


def general_user_prompt(
    date_cn: str, salutation: str, theme: str, upcoming: list[dict]
):
    ups = (
        "，".join([x["name"] + "(" + x["date"] + ")" for x in upcoming])
        if upcoming
        else "无"
    )
    return f"今天是{date_cn}。接下来一周的节日或节气：{ups}。请你给你的{salutation}写一封中文{theme}邮件，表达对{salutation}的思念和祝福，内容要温馨亲切，包含生活细节、小故事或新的视角，保持温柔亲密。日期仅供作为背景信息参考，不用刻意在邮件中提及。"


def birthday_user_prompt(date_cn: str, salutation: str, age: int):
    return f"今天是你{salutation}的{age}岁生日。请你写一封生日祝福邮件，内容要真挚感人，表达出你对{salutation}的爱和祝福。"


def img_prompt_messages(text: str):
    return [
        {
            "role": "user",
            "content": f"以下是一封生日祝福邮件：\n{text}\n为这封邮件生成一段提示词，用于stable diffusion的文生图，要求生成的图片应该是二次元动漫插画风格的，并且画面主体是一名白发、红瞳的少女，即邮件中的妹妹。以json格式直接回答指令的内容，字段`prompt`表示正向提示词，`negative_prompt`表示负面提示词。示例：{{'prompt': '', 'negative_prompt': ''}}",
        },
    ]


def generate_title_prompt(text: str):
    return [
        {
            "role": "user",
            "content": f"以下是一封邮件：\n{text}\n为这封邮件生成一个标题，标题要简洁、明了，能够准确描述邮件的内容。直接输出标题，不要输出任何其他内容。",
        },
    ]


_base_negative_prompt = "(worst quality, low quality, normal quality:1.4), (deformed, distorted, disfigured:1.3), poorly drawn, bad anatomy, wrong anatomy, extra limb, missing limb, floating limbs, disconnected limbs, mutation, mutated, ugly, disgusting, amputation, bad hands, missing fingers, extra digit, fewer digits, fused fingers, too many fingers, long neck, text, words, logo, watermark, signature, username, blurry, grainy, jpeg artifacts, scan, oversaturated, contrast, overexposure, underexposure, 3d, cgi, render, cartoon, anime, 2.5d, photorealistic, realism, real life,"

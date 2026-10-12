import os
import re
from pathlib import Path

from ebooklib import epub

# 输入：md文件。
# 要求文件开头为yaml格式，包含书名、作者信息。yaml可以为空。
# 章节标题和分卷标题使用md格式标题进行标注，标题层级必须从二级开始递增。

# 输出：epub文件。
# 首页为小说名和作者。
# 生成小说目录。


# ^(第[一两二三四五六七八九十零序终百千万0-9. ]+章) *
# ^(第[一两二三四五六七八九十零百千万0-9 ]+[卷集篇部]) *
# ^([^#\n 　-]+ *)
# ## $1

"""
---
书名:
作者:
是否完结:
封面:
---
"""


def get_logger():
    import logging

    log_file = r"output/md_to_epub.log"
    console_handler_level = logging.INFO
    file_handler_level = logging.INFO

    # 创建记录器
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_handler_level)

    # 文件处理器
    file_handler = logging.FileHandler(log_file, encoding="utf-8", mode="w")
    file_handler.setLevel(file_handler_level)

    # 格式化
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # 添加处理器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # 返回日志对象
    return logger


logger = get_logger()


# 正则替换规则
regex_rule = {
    "::1": "全角数字和字母到半角数字和字母的映射",
    "０": "0",
    "１": "1",
    "２": "2",
    "３": "3",
    "４": "4",
    "５": "5",
    "６": "6",
    "７": "7",
    "８": "8",
    "９": "9",
    "Ａ": "A",
    "Ｂ": "B",
    "Ｃ": "C",
    "Ｄ": "D",
    "Ｅ": "E",
    "Ｆ": "F",
    "Ｇ": "G",
    "Ｈ": "H",
    "Ｉ": "I",
    "Ｊ": "J",
    "Ｋ": "K",
    "Ｌ": "L",
    "Ｍ": "M",
    "Ｎ": "N",
    "Ｏ": "O",
    "Ｐ": "P",
    "Ｑ": "Q",
    "Ｒ": "R",
    "Ｓ": "S",
    "Ｔ": "T",
    "Ｕ": "U",
    "Ｖ": "V",
    "Ｗ": "W",
    "Ｘ": "X",
    "Ｙ": "Y",
    "Ｚ": "Z",
    "ａ": "a",
    "ｂ": "b",
    "ｃ": "c",
    "ｄ": "d",
    "ｅ": "e",
    "ｆ": "f",
    "ｇ": "g",
    "ｈ": "h",
    "ｉ": "i",
    "ｊ": "j",
    "ｋ": "k",
    "ｌ": "l",
    "ｍ": "m",
    "ｎ": "n",
    "ｏ": "o",
    "ｐ": "p",
    "ｑ": "q",
    "ｒ": "r",
    "ｓ": "s",
    "ｔ": "t",
    "ｕ": "u",
    "ｖ": "v",
    "ｗ": "w",
    "ｘ": "x",
    "ｙ": "y",
    "ｚ": "z",
    "．": ".",
    "::2": "波浪号处理",
    r"(?<![a-zA-Z0-9])~(?![a-zA-Z0-9])": r"～",
    "::3": "去除空行",
    r"\n+": r"\n",
    "::3": "去除段首段尾空格",
    rf"^[\u0020\u3000\t\u00c2\u00a0]+|[\u0020\u3000\t\u00c2\u00a0]+$": r"",
    "::6": "省略号处理",
    r"[。….]*…+[.。…]*|[.。·]{2,}": r"……",
    "::13": "去除重复省略号",
    r"(\n……)+": r"\n……",
    "::15": "设置分割线",
    r"\n[— \n]+\n": r"\n************\n",
    "::16": "md语法修复：*",
    r"\\(.)": r"\1",
}

css_content = """
/* 选择所有的p元素，设置其样式 */
p {
  /* 设置字体大小为1em */
  font-size: 1em;
  /* 设置首行缩进2em */
  text-indent: 2em;
  /* 设置段落底部外边距为1.25em */
  margin-bottom: 1.25em !important;
  /* 设置文本两端对齐 */
  text-align: justify !important;
}

/* 选择具有title_page类的元素，设置其样式 */
.title_page {
  /* 设置上下内边距为10% */
  padding: 10% 0;
  /* 设置左右外边距自动，使元素在其父容器中水平居中 */
  margin: auto auto;
}

/* 选择具有title类的元素，设置其样式 */
.title {
  /* 重置外边距为0，!important确保该样式优先级最高 */
  margin: 0 !important;
  /* 重置内边距为0，!important确保该样式优先级最高 */
  padding: 0 !important;
  /* 设置文本居中对齐，!important确保该样式优先级最高 */
  text-align: center !important;
  /* 取消首行缩进，!important确保该样式优先级最高 */
  text-indent: 0em !important;
  /* 设置行高为1，!important确保该样式优先级最高 */
  line-height: 1 !important;
  /* 设置字体大小为2em，!important确保该样式优先级最高 */
  font-size: 2em !important;
  /* 设置字体加粗，!important确保该样式优先级最高 */
  font-weight: bold !important;
}

/* 选择具有author类的元素，设置其样式 */
.author {
  /* 重置外边距为0，!important确保该样式优先级最高 */
  margin: 0 !important;
  /* 重置内边距为0，!important确保该样式优先级最高 */
  padding: 0 !important;
  /* 设置文本居中对齐，!important确保该样式优先级最高 */
  text-align: center !important;
  /* 取消首行缩进，!important确保该样式优先级最高 */
  text-indent: 0em !important;
  /* 设置行高为1，!important确保该样式优先级最高 */
  line-height: 1 !important;
  /* 设置字体大小为2em，!important确保该样式优先级最高 */
  font-size: 1.3em !important;
  /* 设置字体粗细，!important确保该样式优先级最高 */
  font-weight: 500 !important;
}
"""


def get_file_list(input_path: str) -> list:
    input_path = input_path.strip().strip('"')
    p = Path(input_path)
    if not p.exists():
        raise Exception("输入路径不存在")
    if p.is_file():
        file_list = [p] if p.suffix == ".md" else []
    elif p.is_dir():
        file_list = [file for file in p.glob("*.md")]
    else:
        raise Exception("输入路径错误")
    if not file_list:
        raise Exception("输入路径下没有md文件")
    return file_list


class MdToEpub:
    def __init__(self, input_path: Path):
        self.path = input_path
        self.book = epub.EpubBook()

    def convert_image_path(self, image_path):
        if not image_path:
            return None
        else:
            image_path = image_path.strip('"')
            image_path = Path(self.path).parent / Path(image_path)
            if not image_path.exists() or not image_path.is_file():
                return None
            # 封面路径转换为绝对路径
            image_path = image_path.resolve()
            # 判断cover_path是否为图片格式的文件，如果不是图片格式的文件，不设置封面
            if image_path.suffix.lower() not in [".jpg", ".jpeg", ".png"]:
                logger.warning(
                    f"\"{image_path}\"图片为不支持的类型，仅支持'.jpg', '.jpeg', '.png'"
                )
                return None
        return image_path

    def get_content(self):
        with self.path.open("r", encoding="utf-8") as f:
            file_content = f.read()
        logger.info(f"正在处理文件：{self.path}")
        yaml_match = re.match(r"---\n(.*?)\n---\n(.*)", file_content, re.DOTALL)

        if yaml_match is not None:
            yaml_block = yaml_match.group(1).strip("\n")
            md_block = yaml_match.group(2).strip("\n")
        else:
            yaml_block = None
            md_block = self.content.strip("\n")

        self.yaml_block = yaml_block
        self.md_block = md_block

    def get_yaml_info(self):
        if self.yaml_block is None:
            yaml_info = {}
        else:
            self.yaml_block = re.sub(r"\n+", r"\n", self.yaml_block)
            yaml_list = self.yaml_block.split("\n")
            yaml_info = {
                key.strip(): value.strip()
                for key, value in [line.split(":", 1) for line in yaml_list]
            }

        title = yaml_info.get("书名", "")
        self.title = title if title else "未知"
        author = yaml_info.get("作者", "")
        self.author = author if author else "佚名"
        cover_path = yaml_info.get("封面", "").strip('"').lstrip("[").rstrip("]")
        self.cover_path = self.convert_image_path(cover_path)

    def split_md(self):
        md_content = self.md_block

        for pattern, replacement in regex_rule.items():
            if pattern.startswith("::"):
                logger.debug(f"{replacement} 正则处理")
                continue
            md_content = re.sub(pattern, replacement, md_content, flags=re.MULTILINE)

        md_content = md_content.strip("\n")

        # 添加默认标题
        if not re.match(r"^#+ .*", md_content):
            md_content = "## 正文\n" + md_content

        chapters = []
        chapter_index = -1
        for line in md_content.split("\n"):
            title_match = re.match(r"#+ (.*)", line)
            if title_match is not None:
                chapter_index += 1
                sub_title = title_match.group(1).strip()
                chapters.append(
                    {
                        "title": sub_title,
                        "level": title_match.group(0).find(" "),
                        "content": [],
                    }
                )
            else:
                chapters[chapter_index]["content"].append(line)

        if min([chapter["level"] for chapter in chapters]) <= 1:
            raise ValueError("不支持一级标题")

        self.chapters += chapters
        logger.debug(f"章节{chapters}")
        logger.info(f"分割章节成功")

    def build_epub(self):
        self.get_content()
        self.get_yaml_info()
        # 设置书籍信息
        self.book.set_identifier("id_" + str(os.urandom(16)))
        self.book.set_language("zh")
        self.book.set_title(self.title)
        self.book.add_author(self.author)
        if self.cover_path:
            # 获取文件扩展名
            ext = self.cover_path.suffix
            # 安全读取文件内容
            with self.cover_path.open("rb") as f:
                cover_data = f.read()
            # 设置封面
            self.book.set_cover(f"cover{ext}", cover_data)

        self.css_item = epub.EpubItem(
            uid="style_css",
            file_name="style.css",
            media_type="text/css",
            content=css_content,
        )
        self.book.add_item(self.css_item)

        epub_chapter = epub.EpubHtml(
            title=f"封面",
            file_name=f"chap_0.xhtml",
            lang="zh",
            content=f"""  <div class="title_page">
    <p><br/></p>
    <p><br/></p>
    <h2 class="title">{self.title}</h2>
    <p><br/></p>
    <p><br/></p>
    <h2 class="author">{self.author}</h2>
  </div>""",
        )
        epub_chapter.add_item(self.css_item)
        self.book.add_item(epub_chapter)
        self.book.spine.append(epub_chapter)
        self.chapters = [
            {"title": "封面", "level": 2, "content": [], "epub_item": epub_chapter}
        ]

        self.add_images()
        self.split_md()
        # for chapter in self.chapters:
        # check_quot(chapter["content"])
        self.build_chapters()
        self.build_toc()

        output_path = self.path.with_suffix(".epub")
        epub.write_epub(output_path, self.book, {"ignore_ncx": False})
        logger.info(f"epub储存在{output_path}")

    def add_images(self):

        # 添加图片到EPUB书籍
        image_pattern = re.compile(r"!\[(.*?)\]\((.*?)\)")
        image_index = 0
        for match in image_pattern.finditer(self.md_block):
            image_index += 1
            md_label = match.group(0)
            alt_text = match.group(1)
            image_path = self.convert_image_path(match.group(2))
            logger.debug(f"图片信息：{md_label},{image_path}")
            if image_path:
                image_name = image_path.name

                html_label = (
                    f'<img alt="{alt_text}" src="images/{image_index}_{image_name}"/>'
                )

                image_item = epub.EpubImage(
                    uid=str(image_index) + "_" + image_name,
                    file_name=f"images/{image_index}_{image_name}",
                    media_type="image/png"
                    if image_name.lower().endswith(".png")
                    else "image/jpeg",
                )
                with image_path.open("rb") as f:
                    image_item.content = f.read()
                self.book.add_item(image_item)

                self.md_block = self.md_block.replace(md_label, html_label)
        if image_index > 0:
            logger.info(f"添加md中的图片")

    def build_chapters(self):
        # 转换并添加所有章节
        for idx, chapter in enumerate(self.chapters[1:], 1):
            chapter_line = chapter["content"]
            if chapter_line == []:
                html_chapter = f"""  <div class="title_page">
    <p><br/></p>
    <p><br/></p>
    <h{chapter["level"]} class=\"title\">{chapter["title"]}</h{chapter["level"]}>
    <p><br/></p>
    <p><br/></p>
  </div>"""

            else:
                html_chapter = (
                    f"<h{chapter['level']}>{chapter['title']}</h{chapter['level']}>\n"
                )
                html_chapter += "\n".join([f"<p>{line}</p>" for line in chapter_line])
            html_chapter = html_chapter.replace(r"<p>************</p>", r"<hr/>")
            epub_chapter = epub.EpubHtml(
                title=f"{chapter['title']}",
                file_name=f"chap_{idx}.xhtml",
                lang="zh",
                content=html_chapter,
            )

            epub_chapter.add_item(self.css_item)

            self.book.add_item(epub_chapter)
            chapter["epub_item"] = epub_chapter
            self.book.spine.append(epub_chapter)

    def build_toc(self):
        sections = []
        for chapter in self.chapters[1:]:
            if chapter["level"] == 2:
                parent_node = None
            else:
                if chapter["level"] == sections[-1]["level"]:
                    parent_node = sections[-1]["parent_node"]
                elif chapter["level"] > sections[-1]["level"]:
                    parent_node = sections[-1]["node"]
                else:
                    for j in range(len(sections) - 1, -1, -1):
                        if chapter["level"] > sections[j]["level"]:
                            parent_node = sections[j]["node"]
                            break
            sections.append(
                {
                    "node": chapter["epub_item"],
                    "level": chapter["level"],
                    "parent_node": parent_node,
                }
            )

        def add_to_toc(sections, parent_node=None):
            toc = []
            sub_sections = [
                sub_section
                for sub_section in sections
                if sub_section["parent_node"] is parent_node
            ]

            for section in sub_sections:
                sub2_sections = [
                    sub2_section
                    for sub2_section in sections
                    if sub2_section["parent_node"] is section["node"]
                ]

                if sub2_sections == []:
                    toc.append(section["node"])
                else:
                    sub_toc = []
                    sub_toc.append(section["node"])
                    sub_toc.append(add_to_toc(sections, section["node"]))
                    toc.append(sub_toc)
            return tuple(toc)

        self.book.toc = add_to_toc(sections)
        # 添加导航文件
        self.book.add_item(epub.EpubNcx())
        self.book.add_item(epub.EpubNav())
        logger.info(f"添加toc成功")


def check_quot(content):
    quot_flag = False
    # quot_flag = Truea
    quot_counter = [0, 0]
    quot_counter2 = 0

    def check_quot_line(content, quot_list):
        content_str = "\n".join(content)
        match = re.findall(
            rf"([{quot_list[0]}{quot_list[1]}])([\S\s\n]*?)([{quot_list[0]}{quot_list[1]}])",
            content_str,
        )
        for quot_item in match:
            if quot_item[0] == quot_list[0] and quot_item[2] == quot_list[1]:
                continue
            else:
                logger.warning(
                    f"警告：行\n{quot_item[0] + quot_item[1] + quot_item[2]}\n引号不匹配，请检查"
                )
                # raise ValueError

        if content_str.count(quot_list[0]) != content_str.count(quot_list[1]):
            quot_item = re.split(rf"[{quot_list[0]}{quot_list[1]}]", content_str)[-1]
            logger.warning(f"警告：行\n{quot_item}\n引号不匹配，请检查")
            # raise ValueError
        # counter = 0
        # for i in quot_list:
        #     counter += line.count(i)
        # if counter % 2 == 1:
        #     quot_counter2 += counter
        #     if quot_counter2 % 2 == 1:

        #         quot_counter2 = counter
        #         logger.warning(f"警告：行\n{line}\n引号不匹配，请检查")

    def replace_quot(line):
        line = list(line)
        for i, chr in enumerate(line):
            if chr in ["“", "”"]:
                quot_counter[0] += 1
                if quot_counter[0] % 2 == 1:
                    line[i] = "「"
                else:
                    line[i] = "」"
            elif chr in ["‘", "’"]:
                quot_counter[1] += 1
                if quot_counter[1] % 2 == 1:
                    line[i] = "『"
                else:
                    line[i] = "』"
        line = "".join(line)
        quot_list = re.findall(r"^[「」]{2,}.+?[「」]{2,}$", line, flags=re.MULTILINE)
        for quot_item in quot_list:
            num = quot_item.count("「")
            line = line.replace(
                quot_item, "「" * num + quot_item[num:-num] + "」" * num
            )
        quot_list = re.findall(r"^[『』]{2,}.+?[『』]{2,}$", line, flags=re.MULTILINE)
        for quot_item in quot_list:
            num = quot_item.count("『")
            line = line.replace(
                quot_item, "『" * num + quot_item[num:-num] + "』" * num
            )
        return line

    BRACKET_CHARS = {"「", "」", "『", "』"}
    if any(char in content for char in BRACKET_CHARS):
        quot_flag = False
        logger.warning("\n警告：文件含有直角引号，请检查\n")

    check_quot_line(
        content,
        [
            "「",
            "」",
        ],
    )
    check_quot_line(
        content,
        [
            "『",
            "』",
        ],
    )
    check_quot_line(content, ["“", "”"])
    check_quot_line(content, ["‘", "’"])
    check_quot_line(content, ["'", "'"])
    check_quot_line(content, ['"', '"'])

    for idx, line in enumerate(content):
        if quot_flag:
            content[idx] = replace_quot(line)
            line = content[idx]
        if (
            tmp := re.search(
                r"^」.*|.*「$|^』.*|.*『$|^”.*|.*“$|^’.*|.*‘$", line, flags=re.MULTILINE
            )
        ) is not None:
            raise ValueError(f"\n{tmp.group(0)}\n引号出错")

    return content


def main(input_path):
    file_list = get_file_list(input_path)
    for file in file_list:
        epub_maker = MdToEpub(file)
        epub_maker.build_epub()
        del epub_maker


if __name__ == "__main__":
    input_path = input("请输入要转换的文件或文件夹路径：").strip(
        '"'
    )  # 去除可能存在的双引号
    # input_path = r"C:\main\var\base\布洛妮娅与希儿的拷问处决.md"
    main(input_path)

import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import unquote

import requests
from dotenv import load_dotenv
from ebooklib import epub

WAIT_TIME = 1
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def utc_to_beijing_no_lib(iso_str: str) -> str:
    dt = datetime.fromisoformat(iso_str)
    bj_dt = dt + timedelta(hours=8)
    return bj_dt.strftime("%Y-%m-%d %H:%M:%S")


css_content = """
/* 选择所有的p元素，设置其样式 */
p {
  /* 设置字体大小为1em */
  font-size: 1em;
  /* 设置首行缩进2em */
  text-indent: 2em;
  /* 设置段落底部外边距为1.25em */
  margin-bottom: 1.25em;

}

h1, h2, h3, h4, h5, h6 {
    font-size: 1.2em;     /* 字号，自己改，比如1.3em */
    font-weight: bold;
    text-align: left;   /* 居中；不需要居中改成 left */
    margin: 1em 0 0.5em 0;
    line-height: 1.3em;
    text-indent: 0;       /* 标题不要首行缩进 */
    page-break-after: avoid; /* 标题不单独留在页底 */
}
.emphasis {
    /* W3C标准 */
    text-emphasis: dot;
    text-emphasis-position: over right;
}
"""


class PixivNovel:
    def __init__(
        self,
        id: int | str,
        cookies: dict[str, str],
        output_path: Path | str = Path("./output"),
        series_flag: bool = True,
    ) -> None:
        self.cookies: dict[str, str] = cookies
        self.headers = HEADERS

        if isinstance(output_path, Path):
            self.output_path = output_path
        else:
            self.output_path = Path(output_path)
        if self.output_path.is_dir() is False:
            raise ValueError("输入的 output 不是目录")

        self.id = int(id)  # 类型转换，输入的id不是数字直接报错
        self.series_flag = bool(series_flag)  # 类型转换，输入的内容不合法直接报错
        self.line_flag = False

    def check_series(self):
        if self.series_flag:
            url = f"https://www.pixiv.net/ajax/novel/series/{self.id}?lang=zh"
            resp = requests.get(url, headers=self.headers, cookies=self.cookies)
            data = resp.json()
            if data.get("error") is True:
                print(f"\n⚠️警告：使用 {self.id} 没有获取到系列章节ID")
                print(f"尝试使用 {self.id} 获取单章小说")
                self.series_flag = False
            else:
                title = data.get("body").get("title")
                author = data.get("body").get("userName")
                self.title = title
                self.author = author

    def get_series_detail(self, series_id, last_order):
        url = f"https://www.pixiv.net/ajax/novel/series_content/{series_id}?limit=30&last_order={last_order}&order_by=asc&lang=zh"
        resp = requests.get(url, headers=self.headers, cookies=self.cookies)
        data = resp.json()
        return data

    def get_novel_detail(self, novel_id):
        url = f"https://www.pixiv.net/ajax/novel/{novel_id}?lang=zh"
        resp = requests.get(url, headers=self.headers, cookies=self.cookies)
        data = resp.json()
        return data

    def get_novel_list(self, series_id):

        id_list = []
        last_order = 0
        while True:
            print(f"\n===== 章节计数：{last_order} =====\n")
            data = self.get_series_detail(series_id, last_order)
            seriesContents = data.get("body").get("page").get("seriesContents")

            if not seriesContents:
                print("已获取所有章节")
                break
                # 将获取到的章节id加入列表
            for item in seriesContents:
                sub_title = item.get("title")
                last_order += 1
                print(f"{last_order:04}:{sub_title}")
                if sub_title is None:
                    continue
                id_list.append(item["id"])

        return id_list

    def get_single_novel(self, novel_id):
        data = self.get_novel_detail(novel_id)

        body = data["body"]
        try:
            title = body["title"]
            author = body["userName"]
            authorId = body["userId"]
            raw_desc = body["description"]
            raw_desc = unquote(raw_desc)
            desc_clean = re.sub(r"<br\s*/?>", "\n", raw_desc)
            raw_content = body["content"]
            raw_pages = raw_content.split("[newpage]")
            upload_date_raw = body["uploadDate"]
            upload_date_bj = utc_to_beijing_no_lib(upload_date_raw)
        except TypeError:
            print(body)
            raise
        full_text = (
            f"## 标题：{title}\n\n"
            f"小说ID：{novel_id}\n\n"
            f"作者：{author}\n\n"
            f"作者ID：{authorId}\n\n"
            f"上传时间：{upload_date_bj}\n\n"
            f"总页数：{len(raw_pages)}\n\n"
            "========================\n\n"
            "【作者前言 / Description】\n\n"
            f"{desc_clean}\n\n"
            "========================\n\n"
        )

        for idx, page_raw in enumerate(raw_pages, start=1):
            page_clean = re.sub(r"<br\s*/?>", "\n", page_raw.strip())
            full_text += f"===== 第{idx}页 =====\n\n{page_clean}\n\n"

        return title, author, full_text

    def download_single(self):
        self.title, self.author, full_text = self.get_single_novel(self.id)
        safe_filename = re.sub(
            r'[<>:"/\\|?*]',
            "_",
            str(self.id) + "_" + self.title + "_" + self.author + ".txt",
        )
        self.file_path = self.output_path / safe_filename
        print(f"\n单章小说获取成功:系列名：{self.title},作者：{self.author}\n")
        with self.file_path.open("w", encoding="utf-8") as f:
            f.write(full_text)
        print(f"✅ 《{self.title}》下载完成\n文件保存在 {self.file_path.absolute()}\n")

    def download_series(self):
        print(f"系列信息获取成功:系列名：{self.title},作者：{self.author}")
        id_list = self.get_novel_list(self.id)
        series_len = len(id_list)
        safe_filename = re.sub(
            r'[<>:"/\\|?*]',
            "_",
            str(self.id) + "_" + self.title + "_" + self.author + ".txt",
        )
        self.file_path = self.output_path / safe_filename
        print(f"\n✅ 一共找到 {series_len} 篇小说，开始下载")
        with self.file_path.open("w", encoding="utf-8") as f:
            for num, id in enumerate(id_list, start=1):
                sub_title, _, full_text = self.get_single_novel(id)
                f.write(full_text)
                print(f"【{num}/{series_len}】《{sub_title}》已下载到文件中")
                time.sleep(WAIT_TIME)
                num += 1
        print(f"\n✅ 所有小说下载完成，文件保存在 {self.file_path.absolute()}\n")

    def download(self):
        self.check_series()
        if self.series_flag is True:
            print(f"\n📖 开始抓取系列：{self.id}")
            self.download_series()
        else:
            print(f"\n📖 开始抓取单篇：{self.id}")
            self.download_single()

        if self.line_flag:
            text = self.file_path.read_text(encoding="utf-8")
            text = re.sub(r"(\S)\n(\S)", r"\1\2", text)
            self.file_path.write_text(text, encoding="utf-8")

    def deal_txt(self):
        with self.file_path.open("r", encoding="utf-8") as f:
            text = f.read()

        # HTML特殊字符转义
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")

        # pixiv特殊字符转义
        text = re.sub(r"\[b:(.*?)\]", r"<b>\1</b>", text)
        text = re.sub(r"\[i:(.*?)\]", r"<i>\1</i>", text)
        text = re.sub(r"\[chapter:(.*?)\]", r"<h3>\1</h3>", text)
        # text = re.sub(r'\[pixivimage:(.*?)\]', "", text)
        # text = re.sub(r'\[uploadedimage:(.*?)\]', "", text)
        # text = re.sub(r"\[jump:(.*?)\]", "", text)
        # text = re.sub(r"\[\[jumpuri:(.*?)\]\]", "", text)
        text = re.sub(
            r"\[\[rb:(.*?) &gt; (.*?)\]\]", r"<ruby>\1<rt>\2</rt></ruby>", text
        )
        text = re.sub(
            r"\[\[emphasismark:(.*?) &gt; •\]\]",
            r'<span class="emphasis">\1</span>',
            text,
        )

        # 按一个或多个空行分割段落（\n 分段）
        paragraphs_raw = text.split("\n")
        p_list = []
        for para in paragraphs_raw:
            para = para.strip()
            if not para:
                continue
            # # 段落内部换行换成 <br>
            # para_html = para.replace("\n", "<br>\n")
            p_list.append(f"<p>{para}</p>")

        body = "\n".join(p_list)
        body = body.replace("<p>## 标题：", "<h2>")
        self.chapter = body.replace("</p>\n<p>小说ID：", "</h2>\n<p>小说ID：")

    def make_epub(self):
        self.deal_txt()
        book = epub.EpubBook()
        book.set_identifier("id_" + str(os.urandom(16)))
        book.set_language("zh")
        book.set_title(self.title)
        book.add_author(self.author)

        css_item = epub.EpubItem(
            uid="style_css",
            file_name="style.css",
            media_type="text/css",
            content=css_content,
        )
        book.add_item(css_item)

        chapters = self.chapter.split("<h2>")
        chapters = chapters[1:]

        toc = []
        for idx in range(len(chapters)):
            chapters[idx] = "<h2>" + chapters[idx]
            pattern = re.compile(r"<h2>(.*?)</h2>")
            result = pattern.findall(chapters[idx])
            chapter_title = result[0]
            epub_chapter = epub.EpubHtml(
                title=f"{chapter_title}",
                file_name=f"chap{idx:04}.xhtml",
                lang="zh",
                content=chapters[idx],
            )
            epub_chapter.add_item(css_item)
            book.add_item(epub_chapter)
            book.spine.append(epub_chapter)
            toc.append(epub_chapter)
        book.toc = toc
        # 添加导航文件
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        self.epub_file = self.file_path.with_suffix(".epub")
        epub.write_epub(self.epub_file, book, {"ignore_ncx": False})
        print(f"epub制作完成，保存在 {self.epub_file}\n")


if __name__ == "__main__":
    # 从环境变量获取重要配置
    load_dotenv(".env")
    PHPSESSID = os.getenv("PHPSESSID")
    line_deal = os.getenv("line_deal")
    save_dir = os.getenv("save_dir")

    if PHPSESSID is None:
        print("PHPSESSID没有设置，可以出现异常\n")
        PHPSESSID = ""
    cookies = {"PHPSESSID": PHPSESSID}

    if save_dir is None:
        save_dir = Path("./output")

    # 部分 pixiv 小说固定长度换行，修改 line_flag 为 true 尝试进行修复
    # line_deal 可批量修改 line_flag
    # line_deal = 12345678_作品_作者.txt,12345678_作品_作者.txt,……
    if line_deal is not None:
        line_deal = line_deal.split(",")
        line_deal = [int(i.strip("").split("_")[0]) for i in line_deal if i]
    else:
        line_deal = []

    # # 批量下载小说
    # id_list = [
    #     "1327205_今天依旧和平的幻想乡_八云诺.txt",
    # ]
    # id_list = [int(i.split("_")[0]) for i in id_list]
    # for i in id_list:
    #     novel = PixivNovel(i, cookies, save_dir)
    #     if novel.id in line_deal:
    #         novel.line_flag = True
    #     novel.download()
    #     novel.make_epub()

    i = input("请输入书籍id：")
    novel = PixivNovel(i, cookies, save_dir)
    if novel.id in line_deal:
        novel.line_flag = True
    novel.download()
    novel.make_epub()

    # # 批量下载小说
    # filec = Path(r"小说id")
    # id_list=[]
    # with filec.open("r",encoding="utf-8") as f:
    #     lista = f.read()
    # id_list =  lista.split("\n")
    # id_list =  [i for i in id_list if i != ""]
    # for i in id_list:
    #     novel = PixivNovel(i, cookies, save_dir)
    #     if novel.id in line_deal:
    #         novel.line_flag = True
    #     novel.download()
    #     novel.make_epub()

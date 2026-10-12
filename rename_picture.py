import pathlib


def rename_photo(work_dir: pathlib.Path):
    """
    批量重命名指定目录下的照片。

    该函数会搜索指定工作目录下所有包含左括号和右括号的文件，并尝试重命名它们。
    重命名规则是取文件名中左括号后和右括号前的字符串，将其补齐为四位数字，然后扩展名不变。

    参数:
    work_dir: 字符串，指定的工作目录路径。
    """
    # 获取工作目录下所有文件的完整路径和文件名，且文件名包含左括号和右括号
    photo_list: list[pathlib.Path] = [
        x
        for x in work_dir.iterdir()
        if x.is_file()
        and "(" in x.name
        and ")" in x.name
        and x.name.index("(") < x.name.index(")")
    ]

    # photo_list: list[pathlib.Path] = [x for x in work_dir.iterdir() if x.is_file()]

    k = 0

    for photo in photo_list:
        # 构造新的文件名，并确保其长度为四位数字
        new_name = (
            photo.parts[-2]
            + "-"
            + photo.name.split("(")[-1].split(")")[-2].rjust(4, "0")
        )

        # new_name = photo.parts[-2] + "-" + photo.stem

        new_photo = photo.with_stem(new_name)

        try:
            # 重命名文件
            photo.rename(new_photo)
            k += 1
        except OSError as e:
            # 如果重命名失败，记录错误信息
            print(f"重命名失败: {photo} -> {new_photo}, 错误: {e}")

    # 输出重命名的照片数量
    print(f"重命名了{k}张照片。")


# 从控制台输入工作目录路径
work_dir = input("请输入工作目录路径: ").strip('"')

# 规范化并获取工作目录的绝对路径
work_dir = pathlib.Path(work_dir).resolve()

# 检查工作目录是否存在
if not work_dir.exists():
    raise Exception("输入的地址有误！")
# 检测work_dir是否为目录
if not work_dir.is_dir():
    raise Exception("输入的地址不是目录！")

# 调用函数重命名照片
rename_photo(work_dir)

# 以下代码被注释掉，未使用
# work_dir_list = [os.path.join(work_dir, x) for x in os.listdir(
#     work_dir) if os.path.isdir(os.path.join(work_dir, x)) is True]
# for i in work_dir_list:
#     rename_photo(i)

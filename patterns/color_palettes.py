"""
Nature 风格配色方案与绘图辅助函数

复用 nature figure skill 中的配色与函数模式。
"""

# 主 Nature 配色 (蓝/橙/绿/红)
PALETTE_NATURE = {
    "blue": "#2E6FAD",
    "orange": "#E09B3E",
    "green": "#5A9E6F",
    "red": "#C75D5D",
    "purple": "#8B6FAF",
    "teal": "#4B9B9B",
    "gold": "#C9A84C",
    "grey": "#7A8A8A",
}
DEFAULT_COLORS = ["#2E6FAD", "#E09B3E", "#5A9E6F", "#C75D5D",
                  "#8B6FAF", "#4B9B9B", "#C9A84C", "#7A8A8A", "#D48B8B"]

# 色盲友好配色
PALETTE_COLORBLIND = {
    "black": "#000000",
    "orange": "#E69F00",
    "sky_blue": "#56B4E9",
    "green": "#009E73",
    "yellow": "#F0E442",
    "blue": "#0072B2",
    "red": "#D55E00",
    "pink": "#CC79A7",
}
COLORBLIND_COLORS = ["#000000", "#E69F00", "#56B4E9", "#009E73",
                     "#F0E442", "#0072B2", "#D55E00", "#CC79A7"]

# 灰度配色
PALETTE_GRAYSCALE = [f"#{i:02x}{i:02x}{i:02x}" for i in range(40, 200, 20)]


def apply_publication_style(font_size=7, axes_linewidth=0.8):
    """应用 Nature 风格 matplotlib 全局设置"""
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "DejaVu Sans", "Liberation Sans"],
        "svg.fonttype": "none",
        "font.size": font_size,
        "axes.linewidth": axes_linewidth,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.major.width": axes_linewidth,
        "ytick.major.width": axes_linewidth,
        "xtick.direction": "out",
        "ytick.direction": "out",
    })


def get_color_palette(name: str = "nature") -> list[str]:
    """获取配色方案的颜色列表"""
    palettes = {
        "nature": DEFAULT_COLORS,
        "colorblind": COLORBLIND_COLORS,
        "grayscale": PALETTE_GRAYSCALE,
    }
    return palettes.get(name.lower(), DEFAULT_COLORS)


def format_colors_prompt(palette: str = "nature") -> str:
    """将配色方案格式化为给 Generator_Coder 的 Prompt 指令"""
    colors = get_color_palette(palette)
    color_names = {
        "nature": "Nature 标准 (蓝#2E6FAD, 橙#E09B3E, 绿#5A9E6F, 红#C75D5D)",
        "colorblind": "色盲友好 (黑, 橙, 天蓝, 绿, 黄, 蓝, 红, 粉)",
        "grayscale": "灰度",
    }
    desc = color_names.get(palette, palette)
    hex_str = ", ".join(colors[:6])
    return f"""使用配色方案: {desc}
推荐颜色 HEX: {hex_str}
请在图例和绘图元素中使用这些颜色。"""

"""Collect relevant icons to icon theme subdirectories

The icons used rely on the KDE breeze theme.

    apt install breeze-icon-theme

This script must be run on a linux machine. Please make sure
that `icon_root` is correct.
"""
import pathlib
import shutil

# Which resolutions to collect
resolutions = ["16"]

# The key identifies the theme; each list contains icon names
icons = {
    "breeze": [
        "application-exit",
        "code-context",
        "documentinfo",
        "document-open",
        "document-save",
        "draw-watercolor",
        "edit-clear",
        "folder-cloud",
        "globe",
        "gtk-preferences",
        "office-chart-ring",
        "office-chart-scatter",
        "show-grid",
        "tools-wizard",
        "view-filter",
        "view-statistics",
        "visibility",
        "path-mode-polyline",
    ],
}

# theme index file
index = """[Icon Theme]
Name=ShapeOutMix
Comment=Mix of themes for Shape-Out 2

Directories={directories}
"""

# theme file folder item
index_item = """
[{directory}]
Size={res}
Type=Fixed
"""

icon_root = pathlib.Path("/usr/share/icons")


def find_icon(name, res, theme):
    cands = sorted((icon_root / theme).rglob("{}.svg".format(name)))
    cands += sorted((icon_root / theme).rglob("{}.png".format(name)))
    rescands = []
    for c in cands:
        if c.parent.name == res or str(c.parent).count("/"+res+"x"+res):
            rescands.append(c)
    if not rescands:
        rescands = cands
        if not cands:
            raise ValueError(
                "Could not find {} / {} / {}".format(theme, res, name))
    return rescands[0]


if __name__ == "__main__":
    directories = []
    here = pathlib.Path(__file__).parent
    for res in resolutions:
        for theme in icons:
            for name in icons[theme]:
                ipath = find_icon(name, res, theme)
                relp = ipath.parent.relative_to(icon_root)
                dest = here / relp
                directories.append(str(relp))
                dest.mkdir(exist_ok=True, parents=True)
                shutil.copy(ipath, dest)

    with (here / "index.theme").open("w") as fd:
        directories = list(set(directories))
        fd.write(index.format(directories=",".join(directories)))
        for dd in directories:
            fd.write(index_item.format(directory=dd, res=res))

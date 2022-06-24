def wand_rendering(svg_str):
    # WARNING! Works only on Windows.
    import wand.image
    with wand.image.Image(blob=svg_str.encode(), format="svg") as image:
        png_image = image.make_blob("png")
    return png_image


def wand_render_from_file(path_to_svg, save_raster_to=None):
    png = wand_rendering(open(path_to_svg).read())
    if save_raster_to is None:
        return png
    with open(save_raster_to, "wb") as f:
        f.write(png)
    return png


def cairo_rendering(svg_str):
    # WARNING! Works only on Linux.
    from cairosvg import svg2png
    return svg2png(bytestring=svg_str)


def cairo_render_from_file(path_to_svg, save_raster_to=None):
    import cairosvg
    if save_raster_to is None:
        return cairosvg.svg2png(url=path_to_svg)
    return cairosvg.svg2png(url=path_to_svg, write_to=save_raster_to)


def svglib_rendering(svg_str):
    # WARNING! <style> tag is not supported!
    import tempfile
    import os
    with tempfile.NamedTemporaryFile(delete=False) as f:
        tmp_filename = f.name
        f.write(svg_str.encode("utf-8"))
    res = svglib_rendering_from_file(tmp_filename)
    os.remove(tmp_filename)
    return res


def svglib_rendering_from_file(svg_filename):
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPM
    drawing = svg2rlg(svg_filename)
    return renderPM.drawToString(drawing, fmt="PNG")

import os
from pathlib import Path
import PIL.Image
from svgpathtools import svg2paths2, wsvg

RASTER_MASK_TARGET = 'tempRasterMasks'
SVG_MASK_TARGET = 'tempSvgMasks'
TEMP_OPTIMIZED = 'tempOptimized'
TEMP = 'temp'

def TEMP_MASK_NAME(idx):
    return RASTER_MASK_TARGET + '/' + TEMP + str(idx) + '.png'

def TEMP_SVG_NAME(idx):
    return SVG_MASK_TARGET + '/' + TEMP + str(idx) + '.svg'

def TEMP_OPTIMIZED_SVG_NAME(idx):
    return SVG_MASK_TARGET + '/' + TEMP_OPTIMIZED + str(idx) + '.svg'

def compileMaskToSvg(idx, mask):
    Path(RASTER_MASK_TARGET).mkdir(parents=True, exist_ok=True)

    PIL.Image.fromarray(mask).save(TEMP_MASK_NAME(idx))
    Path(SVG_MASK_TARGET).mkdir(parents=True, exist_ok=True)

    # TODO: обратить внимание в 2.1 делаю cairo.svg2png, тут тоже должен быть png значит
    os.system('vtracer -i {targetJpg} -g 2 -f 16 -p 8 -s 10 -o {targetSvg}'
              .format(targetJpg = TEMP_MASK_NAME(idx), targetSvg = TEMP_SVG_NAME(idx)))

    # optimizing
    os.system('scour -i {targetSvg} -o {targetOptimizedSvg} --enable-viewboxing --enable-id-stripping --enable-comment-stripping --shorten-ids --indent=none'
              .format(targetSvg=TEMP_SVG_NAME(idx), targetOptimizedSvg=TEMP_OPTIMIZED_SVG_NAME(idx)))

    os.remove(TEMP_SVG_NAME(idx))

def cutSvgByMask(svg_filename, mask_filename): # TODO: отрефакторить этот момент!!!!!!!!
    paths, attributes, svg_attributes = svg2paths2(svg_filename)
    mask_paths, mask_attributes, mask_svg_attributes = svg2paths2(mask_filename)
    in_paths = []
    in_attrs = []
    out_paths = []
    out_attrs = []
    print(len(paths))
    print(len(mask_paths))
    for i in range(len(paths)):
        print(i)
        inside = False
        for mask_path in mask_paths:
            if inside:
                break
            inside = paths[i].is_contained_by(mask_path)
        if inside:
            in_paths.append(paths[i])
            in_attrs.append(attributes[i])
        else:
            out_paths.append(paths[i])
            out_attrs.append(attributes[i])
    print(in_attrs, svg_attributes, len(in_paths))
    wsvg(in_paths, attributes=in_attrs, svg_attributes=svg_attributes, filename='testIN.svg')
    wsvg(out_paths, attributes=out_attrs, svg_attributes=svg_attributes, filename='testOUT.svg')
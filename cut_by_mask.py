import os
import re
import pathlib
import PIL.Image
import svgpathtools
from svg_parser import find_all_used_ids, find_tags_by_ids

RASTER_MASK_TARGET = 'tempRasterMasks'
SVG_MASK_TARGET = 'tempSvgMasks'
TEMP_OPTIMIZED = 'tempOptimized'
TEMP = 'temp'

TEST_IN = 'testIN.svg'
TEST_OUT = 'testOUT.svg'

def TEMP_MASK_NAME(idx):
    return RASTER_MASK_TARGET + '/' + TEMP + str(idx) + '.png'

def TEMP_SVG_NAME(idx):
    return SVG_MASK_TARGET + '/' + TEMP + str(idx) + '.svg'

def TEMP_OPTIMIZED_SVG_NAME(idx):
    return SVG_MASK_TARGET + '/' + TEMP_OPTIMIZED + str(idx) + '.svg'

def compile_mask_to_svg(idx, mask):
    pathlib.Path(RASTER_MASK_TARGET).mkdir(parents=True, exist_ok=True)

    PIL.Image.fromarray(mask).save(TEMP_MASK_NAME(idx))
    pathlib.Path(SVG_MASK_TARGET).mkdir(parents=True, exist_ok=True)

    # TODO: обратить внимание в 2.1 делаю cairo.svg2png, тут тоже должен быть png значит
    os.system('vtracer -i {targetJpg} -g 2 -f 16 -p 8 -s 10 -o {targetSvg}'
              .format(targetJpg = TEMP_MASK_NAME(idx), targetSvg = TEMP_SVG_NAME(idx)))

    # optimizing
    os.system('scour -i {targetSvg} -o {targetOptimizedSvg} --enable-viewboxing --enable-id-stripping --enable-comment-stripping --shorten-ids --indent=none'
              .format(targetSvg=TEMP_SVG_NAME(idx), targetOptimizedSvg=TEMP_OPTIMIZED_SVG_NAME(idx)))

    os.remove(TEMP_SVG_NAME(idx))


def is_contained_by(first, other):
       """Returns true if the path is fully contained in other closed path"""
       if not isinstance(first, svgpathtools.Path):
           return False

       if not first != other:
           return False

       pt = first.point(0)
       xmin, xmax, ymin, ymax = other.bbox()
       pt_in_bbox = (xmin <= pt.real <= xmax) and (ymin <= pt.imag <= ymax)

       if not pt_in_bbox:
           return False

       opt = complex(xmin-1, ymin-1)

       return svgpathtools.path_encloses_pt(pt, opt, other)


def flatten(path, attr):
    args = re.findall(r"[0-9.]+", attr['transform'])
    if len(args) == 0:
        args.append('0')
    if len(args) == 1:
        args.append('0')
    x = float(args[0])
    y = float(args[1])

    return path.translated(x + y * 1j)


def append_common_tags(svg_filename, edit_filename):
    ids = find_all_used_ids(edit_filename)
    tags_to_append = find_tags_by_ids(svg_filename, ids)

    with open(edit_filename, 'r') as f:
        data = f.readlines()

    index_to_write = 0
    for line in data:
        index_to_write += 1
        if line.startswith('<svg'):
            break

    data = data[:index_to_write] + tags_to_append + data[index_to_write:]

    with open(edit_filename, 'w') as f:
        f.writelines(data)


def cut_svg_by_mask(svg_filename, mask_filename): # TODO: отрефакторить этот момент!!!!!!!!
    paths, attributes, svg_attributes = svgpathtools.svg2paths2(svg_filename)
    mask_paths, mask_attributes, mask_svg_attributes = svgpathtools.svg2paths2(mask_filename)

    for i in range(len(mask_paths)):
        mask_paths[i] = flatten(mask_paths[i], mask_attributes[i])

    in_paths = []
    in_attrs = []
    out_paths = []
    out_attrs = []
    print(len(paths))
    print(len(mask_paths))
    for i in range(len(paths)):
        inside = False
        for mask_path in mask_paths:
            if inside:
                break
            inside = is_contained_by(paths[i], mask_path)
        if inside:
            in_paths.append(paths[i])
            in_attrs.append(attributes[i])
        else:
            out_paths.append(paths[i])
            out_attrs.append(attributes[i])

    svgpathtools.wsvg(in_paths, attributes=in_attrs, svg_attributes=svg_attributes, filename=TEST_IN)
    append_common_tags(svg_filename, TEST_IN)

    svgpathtools.wsvg(out_paths, attributes=out_attrs, svg_attributes=svg_attributes, filename=TEST_OUT)
    append_common_tags(svg_filename, TEST_OUT)
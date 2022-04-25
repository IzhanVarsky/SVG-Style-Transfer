import os
import re
import pathlib
import PIL.Image
import svgpathtools
from svg_parser import find_all_used_ids, find_tags_by_ids, remove_white_colors
from os import listdir

RASTER_MASK_TARGET = 'temp/tempRasterMasks'
SVG_MASK_TARGET = 'temp/tempSvgMasks'
CUT_OBJECTS_TARGET = 'temp/tempCutObjects'

TEMP_RASTER = 'tempRaster'
TEMP_SVG = 'tempSvg'
TEMP_OPTIMIZED = 'tempOptimized'
CUT_OBJECT = 'cutObject'

def TEMP_MASK_NAME(idx):
    return f'{RASTER_MASK_TARGET}/{TEMP_RASTER}{str(idx)}.png'

def TEMP_SVG_NAME(idx):
    return f'{SVG_MASK_TARGET}/{TEMP_SVG}{str(idx)}.svg'

def TEMP_OPTIMIZED_SVG_NAME(idx):
    return f'{SVG_MASK_TARGET}/{TEMP_OPTIMIZED}{str(idx)}.svg'

def CUT_OBJECT_SVG_NAME(idx):
    return f'{CUT_OBJECTS_TARGET}/{CUT_OBJECT}{str(idx)}.svg'

def OUT_CUT_OBJECT_SVG_NAME():
    return f'{CUT_OBJECTS_TARGET}/{CUT_OBJECT}Out.svg'

'''
    Save provided raster mask into file and vectorize it
    
    Return: nothing, create file for mask (in svg format)
'''
def compile_mask_to_svg(idx, mask):
    pathlib.Path(RASTER_MASK_TARGET).mkdir(parents=True, exist_ok=True)

    PIL.Image.fromarray(mask).save(TEMP_MASK_NAME(idx))
    pathlib.Path(SVG_MASK_TARGET).mkdir(parents=True, exist_ok=True)

    # TODO: обратить внимание в 2.1 делаю cairo.svg2png, тут тоже должен быть png значит
    os.system('potracer {targetJpg} -o {targetSvg}'
              .format(targetJpg = TEMP_MASK_NAME(idx), targetSvg = TEMP_SVG_NAME(idx)))

    # optimizing
    os.system('scour -i {targetSvg} -o {targetOptimizedSvg} --enable-viewboxing --enable-id-stripping --enable-comment-stripping --shorten-ids --indent=none'
              .format(targetSvg=TEMP_SVG_NAME(idx), targetOptimizedSvg=TEMP_OPTIMIZED_SVG_NAME(idx)))

    # TODO: вот тут удаляем околобелые цвета из свгшки!!!!!!!!
    #filtered_colors = remove_white_colors(TEMP_OPTIMIZED_SVG_NAME(idx))

    #with open(TEMP_OPTIMIZED_SVG_NAME(idx), 'w') as f:
     #   f.writelines('\n'.join(filtered_colors))

    os.remove(TEMP_SVG_NAME(idx))


def path_encloses_pt(pt, opt, path):
    """returns true if pt is a point enclosed by path (which must be a Path
    object satisfying path.isclosed==True).  opt is a point you know is
    NOT enclosed by path."""
    intersections = svgpathtools.Path(svgpathtools.Line(pt, opt)).intersect(path)
    if len(intersections) % 2:
        return True
    else:
        return False


'''
    Determine, whether one path is fully contained by another path
    
    Return: boolean value (true if contained, false otherwise)
'''
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

       return path_encloses_pt(pt, opt, other)


'''
    Flatten transformations in the given path
    
    Return: the same path without transforms
'''
def flatten(path, attr):
    if 'transform' not in attr:
        return path

    args = re.findall(r"[0-9.]+", attr['transform'])
    if len(args) == 0:
        args.append('0')
    if len(args) == 1:
        args.append('0')
    x = float(args[0])
    y = float(args[1])

    return path.translated(x + y * 1j) # TODO: добавить еще какие-нибудь трансформации


'''
    Extract ids used in paths from edit_filename, find declarations of them in svg_filename
    And write them in edit_filename
    
    Return: nothing, edit file and write declarations of ids in it
'''
def append_common_tags(svg_filename, edit_filename, ids = None):
    if ids == None: # TODO: check this
        ids = find_all_used_ids(edit_filename)
    tags_to_append = find_tags_by_ids(svg_filename, ids)

    with open(edit_filename, 'r') as f:
        data = f.readlines()

    index_to_write = 0
    for line in data:
        index_to_write += 1
        if line.startswith('<svg'):
            break

    tags_to_append = list(map(lambda line: line + '\n', tags_to_append))
    data = data[:index_to_write] + tags_to_append + data[index_to_write:]

    with open(edit_filename, 'w') as f:
        f.writelines(data)


'''
    Cut object of one type in svg_filename by provided mask_filename
    
    Return: nothing, create file for objects inside mask and outside it
'''
def cut_svg_by_mask(svg_filename, mask_filename, idx, remained_objects): # TODO: отрефакторить этот момент!!!!!!!!
    if (idx == 0):
        # TODO: вот тут можно не прокидывать свг и индекс, а делать это внутри
        remained_objects = svg_filename
    paths, attributes, svg_attributes = svgpathtools.svg2paths2(remained_objects)
    mask_paths, mask_attributes, mask_svg_attributes = svgpathtools.svg2paths2(mask_filename)

    for i in range(len(mask_paths)):
        mask_paths[i] = flatten(mask_paths[i], mask_attributes[i])

    in_paths = []
    in_attrs = []
    out_paths = []
    out_attrs = []
    for i in range(len(paths)):
        inside = False
        for mask_path in mask_paths:
            if inside:
                break
            inside = is_contained_by(mask_path, paths[i])
        if inside:
            in_paths.append(paths[i])
            in_attrs.append(attributes[i])
        else:
            out_paths.append(paths[i])
            out_attrs.append(attributes[i])

    if (len(in_paths) != 0):
        svgpathtools.wsvg(in_paths, attributes=in_attrs, svg_attributes=svg_attributes, filename=CUT_OBJECT_SVG_NAME(idx))
        append_common_tags(svg_filename, CUT_OBJECT_SVG_NAME(idx))

    # out of mask
    if (len(out_paths) != 0):
        if (os.path.exists(OUT_CUT_OBJECT_SVG_NAME())):
            os.remove(OUT_CUT_OBJECT_SVG_NAME())

        svgpathtools.wsvg(out_paths, attributes=out_attrs, svg_attributes=svg_attributes, filename=OUT_CUT_OBJECT_SVG_NAME())
        append_common_tags(svg_filename, OUT_CUT_OBJECT_SVG_NAME())


'''
    Cut from svg_filename objects by svg masks in SVG_MASK_TARGET folder

    Return: list of filenames of svg cut objects from masks
'''
def cut_all_svg_by_mask(svg_filename):
    pathlib.Path(CUT_OBJECTS_TARGET).mkdir(parents=True, exist_ok=True)

    for idx, svg_mask in enumerate(listdir(SVG_MASK_TARGET)):
        cut_svg_by_mask(svg_filename, f'{SVG_MASK_TARGET}/{svg_mask}', idx, OUT_CUT_OBJECT_SVG_NAME())

    cut_objects_filenames = map(lambda cur_name: f'{CUT_OBJECTS_TARGET}/{cur_name}', os.listdir(CUT_OBJECTS_TARGET))

    return cut_objects_filenames
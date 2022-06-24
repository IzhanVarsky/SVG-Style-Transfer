import codecs
import cv2 as cv
import numpy
import PIL.Image
import io
from segmentation import Segmentation
from cut_by_mask import compile_mask_to_svg, cut_svg_by_mask, cut_all_svg_by_mask
from color_transfer import transfer_style
from svg_parser import remove_groups_and_enumerate, sort_paths_tags
from gram_loss import style_loss
from svg_render import cairo_render_from_file, wand_render_from_file

DIM = (500, 300)
INF = 1000000
segmentaizer = Segmentation()

render_func = wand_render_from_file


def read_image(path_to_image):
    image = cv.imread(path_to_image)
    image = cv.cvtColor(image, cv.COLOR_BGR2RGB)
    image = cv.resize(image, DIM, interpolation=cv.INTER_AREA)

    return image


def read_svg(path_to_svg):
    with codecs.open(path_to_svg, encoding='utf-8', errors='ignore') as f:
        svg = f.read()

        return svg


'''
 I. Processing raster image (style):
    1) Segment image to different classes of objects (class of 'trees', class of 'sky', etc)
    2) Cut the mask for every certain class. The mask should contains objects only from one type,
       while everything else should be covered with 'black' color (rgb (0, 0, 0))
       
    Result: raster images with mask of objects for every class and top-{NUMBER_OF_CLASSES} predicted classes
'''


def process_style(path_to_style):
    masks, predicted_classes = segmentaizer.segment(path_to_style)
    return masks, predicted_classes


'''
 II. Processing vector image (that we want to recolor):
    0) Pre - flatten all transforms and delete groups, also enumerate paths
    1) Transform it to raster image with library 'cairosvg'
    2) Repeat I.1) - segment image to different classes of objects (class of 'trees', class of 'sky', etc)
    3) Cut the silhouette for every certain class. Silhouette - two-color image.
    4) Process every mask - vectorization mask into SVG.
    5) This vector we will use for library 'svgtools'
       to split processing SVG file into two vector. First vector will contain only objects from certain class
       (which belong to current mask), another vector will not contain it. Now we will continue loop with
       new vector (without objects from current class)
    
    Result: vectors where the each vector contain objects only from certain class
'''


def process_svg(path_to_svg, predicted_style_obects):
    # II.0)
    path_to_svg = remove_groups_and_enumerate(path_to_svg)
    # II.1)
    rasterized = render_func(path_to_svg)
    # II.2) and II.3)
    silhouettes, predicted_classes = segmentaizer.segment(rasterized, from_byte=True, silhouette=True,
                                                          predicted_style_obects=predicted_style_obects)
    # II.4)
    for idx, silhouette in enumerate(silhouettes):
        compile_mask_to_svg(idx, silhouette)

    # II.5)
    svg_cut_objects_filenames = cut_all_svg_by_mask(path_to_svg)

    return svg_cut_objects_filenames


def full_style_transfer(style_filename, content_filename, save_svg):
    pil_image = PIL.Image.open(style_filename).convert('RGB')
    style = numpy.array(pil_image)
    result_pathfile = transfer_style(style, content_filename, True, save_svg)

    return result_pathfile


def make_transfer_style(content_path, style_path, save_raster_to, save_full_raster_to, save_svg_to, save_full_svg_to):
    loss = INF
    full_trasfer_loss = INF

    try:
        styleMasks, style_classes = process_style(style_path)
        svg_masks_filenames = process_svg(content_path, style_classes)

        result_pathfile = None
        content_idx = 0
        for style_idx, style_mask in enumerate(styleMasks):
            svg_filename = svg_masks_filenames[content_idx]
            if (str(style_idx) not in svg_filename) and (style_idx != len(styleMasks) - 1):
                continue
            # print(f'Now processing mask number {idx}')
            print(content_idx, style_idx)
            content_idx += 1
            result_pathfile = transfer_style(style_mask, svg_filename, content_idx == 1, save_svg_to)

        if result_pathfile is not None:
            sort_paths_tags(result_pathfile)

        render_func(result_pathfile, save_raster_to)
        loss = style_loss(result_image=save_raster_to, style_image=style_path)
    except Exception:
        pass

    try:
        render_func(full_style_transfer(style_path, content_path, save_full_svg_to),
                    save_full_raster_to)
        full_trasfer_loss = style_loss(result_image=save_full_raster_to, style_image=style_path)
    except Exception:
        pass

    return loss, full_trasfer_loss


if __name__ == '__main__':
    ## test stand
    loss, full_trasfer_loss = make_transfer_style('3742013529.svg', 'istockphoto-168643984-612x612.jpg', 'result_gram.png',
                                                  'full_result_gram.png', 'result_svg.svg', 'full_result_svg.svg')
    print(loss, full_trasfer_loss)

    # Метрики Грама TODO
    # print('Their', style_loss(result_image='test_gram_2.png', style_image='test_gram_1.jpeg'))

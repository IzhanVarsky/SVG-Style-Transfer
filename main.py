import codecs
import cv2 as cv
import cairosvg
from segmentation.segmentation import Segmentation
from cut_by_mask import compile_mask_to_svg, cut_svg_by_mask, cut_all_svg_by_mask
from color_transfer_legacy import transfer_style
from svg_parser import remove_groups

# TODO: provide NUMBER_OF_CLASSES into segmentation by constructor or check
# the score and add threshold (to filter classes with low score of likeness)

# TODO: what if some objects can not be segment? How to change color or extract?
# think about it and add it to documentary (plan with points)

# TODO: do not create file for vectorize silhouettes (II.4))

DIM = (500, 300)
segmentaizer = Segmentation()

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
       
    Result: raster images with mask of objects for every class
'''
def process_style(path_to_style):
    masks = segmentaizer.segment(path_to_style)
    return masks

'''
 II. Processing vector image (that we want to recolor):
    0) Pre - flatten all transforms and delete groups
    1) Transform it to raster image with library 'cairosvg'
    2) Repeat I.1) - segment image to different classes of objects (class of 'trees', class of 'sky', etc)
    3) Cut the silhouette for every certain class. Silhouette - two-color image.
    4) Process every mask - vectorization mask into SVG. # TODO: do not create file for it
    5) This vector we will use for library 'svgtools'
       to split processing SVG file into two vector. First vector will contain only objects from certain class
       (which belong to current mask), another vector will not contain it. Now we will continue loop with
       new vector (without objects from current class)
    
    Result: vectors where the each vector contain objects only from certain class
'''
def process_svg(path_to_svg):
    # II.0)
    path_to_svg = remove_groups(path_to_svg)
    # TODO: добавить вот сюда дерганье flatten как-нибудь + мой svg_parser
    # II.1)
    rasterized = cairosvg.svg2png(url=path_to_svg)
    # II.2) and II.3)
    silhouettes = segmentaizer.segment(rasterized, from_byte=True, silhouette=True)
    # II.4)
    for idx, silhouette in enumerate(silhouettes):
        compile_mask_to_svg(idx, silhouette)

    # II.5)
    svg_cut_objects_filenames = cut_all_svg_by_mask(path_to_svg)

    return svg_cut_objects_filenames

## test stand
styleMasks = process_style('sample1.jpg')
svg_masks_filenames = process_svg('sample2 (result).svg')
print(svg_masks_filenames)

for idx, (style_mask, svg_filename) in enumerate(zip(styleMasks + [styleMasks[0]], svg_masks_filenames)):
    print(f'Now processing mask number {idx}')
    transfer_style(style_mask, svg_filename, idx == 0)

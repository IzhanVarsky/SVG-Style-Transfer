from os import listdir
from main import make_transfer_style

SVGS = 'metrics/svg_dataset'
RASTER_RESULT = 'metrics/raster_result'
FULL_RASTER_RESULT = 'metrics/full_raster_result'
SVG_RESULT = 'metrics/svg_result'
FULL_SVG_RESULT = 'metrics/full_svg_result'

open('metrics.txt', 'w').close()

for idx, name in enumerate(listdir(SVGS)):
    cur_svg = f'{SVGS}/{name}'
    name_without_ext = name.split('.')[0]
    print('Index:', idx)
    print('Current svg', cur_svg)
    style_path = 'sample1recolor.jpg'


    raster = f'{RASTER_RESULT}/{name_without_ext}.png'
    full_raster = f'{FULL_RASTER_RESULT}/{name_without_ext}.png'
    svg = f'{SVG_RESULT}/{name_without_ext}.svg'
    full_svg = f'{FULL_SVG_RESULT}/{name_without_ext}.svg'

    loss, full_loss = make_transfer_style(cur_svg, style_path, raster, full_raster, svg, full_svg)
    with open('metrics.txt', 'a') as f:
        f.write(f'{idx};{loss};{full_loss};\n')
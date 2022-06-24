import codecs
import os
import re
import shutil
from pathlib import Path
import cv2 as cv
import matplotlib.pyplot as plt
import numpy as np
import svgpathtools
from skimage import color
from sklearn.cluster import KMeans
from cut_by_mask import find_all_used_ids, append_common_tags
from svg_parser import find_paths

DIM = (500, 300)
COLORS_IN_PALETTE = 6

STYLE_TRANSFERED_SVG = 'styleTransferedSvg.svg'
NEW_CONTENT_TEMP_SVG = 'tempNewContentSvg.svg'
NUMBER_EXAMPLES = 1


def show_img_compar(img_1):
    imgplot = plt.imshow(img_1)
    plt.axis('off')
    plt.show()


def rgb2lab(arr):
    return color.rgb2lab(arr)


def lab2rgb(arr):
    return color.lab2rgb(arr)


def labRgbMult255(array):
    rgbCentres = []
    for arr in array:
        arr = lab2rgb(arr)
        arr[0] *= 255
        arr[1] *= 255
        arr[2] *= 255
        rgbCentres.append(arr)

    return np.array(rgbCentres)


def toRGB(hexa):
    return tuple(int(hexa[i:i + 2], 16) / 255 for i in (0, 2, 4))


def toHex(rgb):
    return '#%02x%02x%02x' % rgb


# extract main colors from "file-color"
def extractPalette(img, count_colors):
    lab = rgb2lab(img)
    clusters = KMeans(n_clusters=count_colors)
    imgShaped = lab.reshape(-1, 3)
    clusters.fit(imgShaped)

    rgbCentres = labRgbMult255(clusters.cluster_centers_)

    width = 600
    showImg = np.zeros((100, width, 3), np.uint8)
    steps = width / rgbCentres.shape[0]
    for idx, centers in enumerate(rgbCentres):
        showImg[:, int(idx * steps):(int((idx + 1) * steps)), :] = centers
    # show_img_compar(showImg)

    rgbTuples = tuple(map(tuple, rgbCentres.astype(int)))
    hexColors = []
    cluster_centers = []
    for idx, tupl in enumerate(rgbTuples):
        # r, g, b = tupl
        # if (r > 240 and g > 240 and b > 240):
        #   continue
        hexColors.append('#%02x%02x%02x' % tupl)
        cluster_centers.append(clusters.cluster_centers_[idx])
    return hexColors, cluster_centers


def findIndex(curColor, array):
    for idx, sub in enumerate(array):
        if np.array_equal(sub, curColor):
            return idx


def findByValue(hexToLab, value):
    return list(hexToLab.keys())[findIndex(value, list(hexToLab.values()))]


def changeColors(content, palette, is_sorted_version=True):
    colorsToChange = re.findall(r"#[0-9a-fA-F]{6}", content)
    colorsToChange = list(dict.fromkeys(colorsToChange))

    allColors = colorsToChange
    allHEX = colorsToChange + palette[0]

    # print(len(allColors), 'colors were found in this file\n')
    allColors = [toRGB(hexaHashTag[1:]) for hexaHashTag in allColors]

    lab = np.concatenate((rgb2lab(allColors), palette[1]), axis=0)

    hexToLab = dict(zip(allHEX, lab))

    allLAB = lab.reshape(-1, 3)
    allLAB = allLAB[np.apply_along_axis(lambda row: euclidean((row[0], row[1], row[2])), 1, allLAB).argsort()]

    indexes = [findIndex(i, allLAB) for i in palette[1]]
    indexes.sort()

    frequency_index_change = (len(allLAB) - len(indexes)) // len(indexes) + 1
    # сколько индексов не из списка (indexes) уже прошло
    true_indecies_spent = 0
    curColorIndex = 0
    for idx, color in enumerate(allLAB):
        if (idx in indexes):
            if is_sorted_version:
                curColorIndex = min(curColorIndex + 1, len(indexes) - 1)
            else:
                if true_indecies_spent % frequency_index_change == 0:
                    curColorIndex = min(curColorIndex + 1, len(indexes) - 1)
        else:
            true_indecies_spent += 1
            color1 = findByValue(hexToLab, color)
            color2 = findByValue(hexToLab, allLAB[indexes[curColorIndex]])
            content = content.replace(color1.upper(), color2.upper())
            content = content.replace(color1, color2.upper())
    return content


def euclidean(coords):
    ll, aa, bb = (0, -128, -128)  # lab0
    l, a, b = coords
    return (l - ll) ** 2 + (a - aa) ** 2 + (b - bb) ** 2


'''

    Return: filename of resulting svg (with transfered style)
'''


def transfer_style(style, content_filename, is_first_file=False, save_to_path=None):
    style = cv.resize(style, DIM, interpolation=cv.INTER_AREA)
    if save_to_path is None:
        save_to_path = STYLE_TRANSFERED_SVG

    palette = extractPalette(style, COLORS_IN_PALETTE)

    with codecs.open(content_filename, encoding='utf-8', errors='ignore') as f:
        content = f.read()

    print('Now processing file', content_filename)
    newContent = changeColors(content, palette)
    # Если первый файл, то просто выдаем то что есть и уходим
    if is_first_file:
        with open(save_to_path, 'wb') as f:
            f.write(newContent.encode('utf-8'))
        return save_to_path

    # Иначе начинаем добавлять в существующий файл
    with open(NEW_CONTENT_TEMP_SVG, 'wb') as f:
        f.write(newContent.encode('utf-8'))

    # Вставляем id для градиентов всяких
    ids_content = find_all_used_ids(NEW_CONTENT_TEMP_SVG)
    ids_already_in_result = find_all_used_ids(save_to_path)

    ids_to_add = list(filter(lambda id: id not in ids_already_in_result, ids_content))

    append_common_tags(NEW_CONTENT_TEMP_SVG, save_to_path, ids_to_add)

    # Переносим пути из текущего контента (NEW_CONTENT_TEMP_SVG) в общий файл (save_to_path)
    paths_new_content = find_paths(newContent)

    with open(save_to_path, 'r') as f:
        data = f.readlines()

        index_to_write = len(data) - 1

        paths_new_content = list(map(lambda line: line + '\n', paths_new_content))
        data = data[:index_to_write] + paths_new_content + data[index_to_write:]

    with open(save_to_path, 'w') as f:
        f.writelines(data)

    os.remove(NEW_CONTENT_TEMP_SVG)

    return save_to_path

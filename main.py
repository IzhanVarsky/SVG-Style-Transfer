import codecs
from sklearn.cluster import KMeans
import numpy as np
import cv2 as cv
import os
import re
import random
from PIL import ImageColor
from pathlib import Path
import matplotlib.pyplot as plt
import math
import copy
import colorsys
import shutil

DIM = (500, 300)
COLORS_IN_PALETTE = 10

WHITE_COLOR_FILTER = 220

JPG_SOURCE_FOLDER = 'images/jpg'
SVG_SOURCE_FOLDER = 'images/svg'
TARGET_FOLDER = 'target'
STYLE_SOURCE = 'style5.jpg'


def show_img_compar(img_1, img_2 ):
    imgplot = plt.imshow(img_1)
    plt.axis('off')
    plt.show()

# extract main colors from "file-color"
def extractPalette(img, count_colors):
    clusters = KMeans(n_clusters=count_colors)
    imgShaped = img.reshape(-1, 3)
    imgFilter = []
    for rgb in imgShaped:
        if rgb[0] > WHITE_COLOR_FILTER and rgb[1] > WHITE_COLOR_FILTER and rgb[2] > WHITE_COLOR_FILTER:
            continue
        imgFilter.append(rgb)
    clusters.fit(imgFilter)

    width = 600
    showImg = np.zeros((100, width, 3), np.uint8)
    steps = width / clusters.cluster_centers_.shape[0]
    for idx, centers in enumerate(clusters.cluster_centers_):
        showImg[:, int(idx * steps):(int((idx + 1) * steps)), :] = centers
    show_img_compar(showImg, showImg)

    rgbTuples = tuple(map(tuple, clusters.cluster_centers_.astype(int)))
    rgbColors = []
    for tupl in rgbTuples:
        print(tupl)
        rgbColors.append('#%02x%02x%02x' % tupl)
    return rgbColors


def changeColors(content, palette):
    colorsToChange = re.findall(r"#\w+", content)
    colorsToChange = list(dict.fromkeys(colorsToChange))

    allColors = palette + colorsToChange
    allColors = [toRGB(hexaHashTag[1:]) for hexaHashTag in allColors]
    allColors.sort(key=lambda x: step(x, 8))
    allColors = [toHex(i) for i in allColors]

    indexes = [allColors.index(i) for i in palette]
    indexes.sort()

    curColorIndex = 0
    for idx, color in enumerate(allColors):
        if (idx in indexes):
            curColorIndex = min(curColorIndex + 1, len(indexes) - 1)
        else:
            content = content.replace(color.upper(), allColors[indexes[curColorIndex]].upper())
    return content


def compileJpgToSvg():
    shutil.rmtree(SVG_SOURCE_FOLDER, ignore_errors=True)
    Path(SVG_SOURCE_FOLDER).mkdir(parents=True, exist_ok=True)
    filesToCompile = os.listdir(JPG_SOURCE_FOLDER)
    random.shuffle(filesToCompile)
    for fileToCompile in filesToCompile[0:20]:
        fileName = os.path.splitext(fileToCompile)[0]
        os.system('vtracer -i {sourceJpg}/{name}.jpg -g 2 -f 16 -p 8 -s 10 -o {sourceSvg}/{name}.svg'.format(name = fileName, sourceJpg = JPG_SOURCE_FOLDER, sourceSvg = SVG_SOURCE_FOLDER))



def toRGB(hexa):
    return tuple(int(hexa[i:i + 2], 16) for i in (0, 2, 4))


def toHex(rgb):
    return '#%02x%02x%02x' % rgb


def step(x, repetitions=1):
    r = x[0]
    g = x[1]
    b = x[2]
    lum = math.sqrt(.241 * r + .691 * g + .068 * b)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    h2 = int(h * repetitions)
    lum2 = int(lum * repetitions)
    v2 = int(v * repetitions)
    if h2 % 2 == 1:
        v2 = repetitions - v2
        lum = repetitions - lum
    return (h2, lum, v2)


style = cv.imread(STYLE_SOURCE)
style = cv.cvtColor(style, cv.COLOR_BGR2RGB)
style = cv.resize(style, DIM, interpolation=cv.INTER_AREA)

palette = extractPalette(style, COLORS_IN_PALETTE)

compileJpgToSvg()
print('All svg compiled')

filesToChange = os.listdir(SVG_SOURCE_FOLDER)
shutil.rmtree(TARGET_FOLDER, ignore_errors=True)
Path(TARGET_FOLDER).mkdir(parents=True, exist_ok=True)

for fileToChange in filesToChange:
    with codecs.open(SVG_SOURCE_FOLDER + '/' + fileToChange, encoding='utf-8', errors='ignore') as f:
            content = f.read()

    newContent = changeColors(content, palette)

    with open(TARGET_FOLDER + '/' + fileToChange, 'wb') as f:
        f.write(newContent.encode('utf-8'))



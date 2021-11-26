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
from skimage import io, color
from functools import cmp_to_key

DIM = (500, 300)
COLORS_IN_PALETTE = 10

WHITE_COLOR_FILTER = 220

JPG_SOURCE_FOLDER = 'images/jpg'
SVG_SOURCE_FOLDER = 'images/svg'
TARGET_FOLDER = 'target'
STYLE_SOURCE = 'style8.jpg'
NUMBER_EXAMPLES = 1


def show_img_compar(img_1, img_2 ):
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

# extract main colors from "file-color"
def extractPalette(img, count_colors):
    lab = rgb2lab(img)
    clusters = KMeans(n_clusters=count_colors)
    imgShaped = lab.reshape(-1, 3)
    imgFilter = []
    for rgb in imgShaped:
        #if rgb[0] > WHITE_COLOR_FILTER and rgb[1] > WHITE_COLOR_FILTER and rgb[2] > WHITE_COLOR_FILTER:
         #   continue
        imgFilter.append(rgb)
    clusters.fit(imgFilter)

    rgbCentres = labRgbMult255(clusters.cluster_centers_)

    width = 600
    showImg = np.zeros((100, width, 3), np.uint8)
    steps = width / rgbCentres.shape[0]
    for idx, centers in enumerate(rgbCentres):
        showImg[:, int(idx * steps):(int((idx + 1) * steps)), :] = centers
    show_img_compar(showImg, showImg)

    rgbTuples = tuple(map(tuple, rgbCentres.astype(int)))
    hexColors = []
    for tupl in rgbTuples:
        hexColors.append('#%02x%02x%02x' % tupl)
    return (hexColors, clusters.cluster_centers_)

def findIndex(curColor, array):
    for idx, sub in enumerate(array):
        if np.array_equal(sub, curColor):
            return idx

def findByValue(hexToLab, value):
    return list(hexToLab.keys())[findIndex(value, list(hexToLab.values()))]

def changeColors(content, palette):
    colorsToChange = re.findall(r"#\w+", content)
    colorsToChange = list(dict.fromkeys(colorsToChange))

    allColors = colorsToChange
    allHEX = colorsToChange + palette[0]
    print(len(allColors))
    allColors = [toRGB(hexaHashTag[1:]) for hexaHashTag in allColors]

    lab = np.concatenate((rgb2lab(allColors), palette[1]), axis=0)

    hexToLab = dict(zip(allHEX, lab))

    allLAB = lab.reshape(-1, 3)
    allLAB = allLAB[np.apply_along_axis(lambda row: euclidean((row[0], row[1], row[2])), 1, allLAB).argsort()]

    indexes = [findIndex(i, allLAB) for i in palette[1]]
    indexes.sort()

    curColorIndex = 0
    for idx, color in enumerate(allLAB):
        if (idx in indexes):
            curColorIndex = min(curColorIndex + 1, len(indexes) - 1)
        else:
            color1 = findByValue(hexToLab, color)
            color2 = findByValue(hexToLab, allLAB[indexes[curColorIndex]])
            content = content.replace(color1.upper(), color2.upper())
    return content


def compileJpgToSvg():
    shutil.rmtree(SVG_SOURCE_FOLDER, ignore_errors=True)
    Path(SVG_SOURCE_FOLDER).mkdir(parents=True, exist_ok=True)
    filesToCompile = os.listdir(JPG_SOURCE_FOLDER)
    random.shuffle(filesToCompile)
    for fileToCompile in filesToCompile[0:NUMBER_EXAMPLES]:
        fileName = os.path.splitext(fileToCompile)[0] #or -f 16
        os.system('vtracer -i {sourceJpg}/{name}.jpg -g 2 -f 16 -p 8 -s 10 -o {sourceSvg}/{name}.svg'.format(name = fileName, sourceJpg = JPG_SOURCE_FOLDER, sourceSvg = SVG_SOURCE_FOLDER))



def toRGB(hexa):
    return tuple(int(hexa[i:i + 2], 16) / 255 for i in (0, 2, 4))


def toHex(rgb):
    return '#%02x%02x%02x' % rgb

def euclidean(coords):
    ll, aa, bb = (0, -128, -128) #lab0
    l, a, b = coords
    return (l - ll) ** 2 + (a - aa) ** 2 + (b - bb) ** 2


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



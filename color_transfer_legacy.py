import codecs
import os
import re
import shutil
from pathlib import Path
import cv2 as cv
import matplotlib.pyplot as plt
import numpy as np
from skimage import color
from sklearn.cluster import KMeans

DIM = (500, 300)
COLORS_IN_PALETTE = 6

SVG_SOURCE_FOLDER = 'images/svg'
TARGET_FOLDER = 'target'
STYLE_SOURCE = 'styles/sample1.jpg'
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
    show_img_compar(showImg)

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
    colorsToChange = re.findall(r"#[0-9a-fA-F]{6}", content)
    colorsToChange = list(dict.fromkeys(colorsToChange))

    allColors = colorsToChange
    allHEX = colorsToChange + palette[0]
    print(allColors)
    print(palette[0])
    print(len(allColors), 'colors were found in this file\n')
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
            content = content.replace(color1, color2.upper())
    return content

def euclidean(coords):
    ll, aa, bb = (0, -128, -128) #lab0
    l, a, b = coords
    return (l - ll) ** 2 + (a - aa) ** 2 + (b - bb) ** 2


style = cv.imread(STYLE_SOURCE)
style = cv.cvtColor(style, cv.COLOR_BGR2RGB)
style = cv.resize(style, DIM, interpolation=cv.INTER_AREA)

palette = extractPalette(style, COLORS_IN_PALETTE)


filesToChange = os.listdir(SVG_SOURCE_FOLDER)
shutil.rmtree(TARGET_FOLDER, ignore_errors=True)
Path(TARGET_FOLDER).mkdir(parents=True, exist_ok=True)

for fileToChange in filesToChange:
    with codecs.open(SVG_SOURCE_FOLDER + '/' + fileToChange, encoding='utf-8', errors='ignore') as f:
            content = f.read()

    print('Now processing file', fileToChange)
    newContent = changeColors(content, palette)

    with open(TARGET_FOLDER + '/result-' + fileToChange, 'wb') as f:
        f.write(newContent.encode('utf-8'))






# legacy svg_parser
import re
import codecs

def find_pair_group(arr):
    balance = 0
    startPosition = -1
    endPosition = -1

    for idx, tag in enumerate(arr):
        if tag.startswith('<g'):
            if balance == 0:
                startPosition = idx
            balance += 1
        if tag.startswith('</g'):
            if balance == 1:
                endPosition = idx
                break
            balance -= 1

    return startPosition, endPosition

def inherit_attributes(tag):
    attributes_dict = {}
    attributes = re.findall(r"[a-z-A-Z0-9]*=\".*?\"", tag)
    for attribute in attributes:
        key, value = attribute.split('=')
        attributes_dict[key] = value.replace('"', '')
    return attributes_dict

def clean_attributes(tag):
    tag = re.sub(r"[a-z-A-Z0-9]*=\".*?\"", '', tag)
    return re.sub(r"\s*", '', tag)

def add_attributes(tag, attrs):
    tag = clean_attributes(tag)
    ind = len(tag) - 1 # before this index we need to insert attributes
    if tag[ind - 1] == '/':
        ind -= 1
    attrs_string = ''

    for attr in attrs:
        attrs_string += (' ' + attr + '="' + attrs[attr] + '"')
    return tag[:ind] + attrs_string + tag[ind:]


def extend_attributes(group_attributes, group_position, tags):
    start_group, end_group = group_position
    for i in range(start_group + 1, end_group - 1):
        cur_tag = tags[i]
        if cur_tag.startswith('</'):
            continue
        cur_tag_attributes = inherit_attributes(cur_tag)

        '''
        for attr in group_attributes: # может быть заигнорить атрибут d
            if attr in cur_tag_attributes:
                if (attr == "fill-rule" or attr == "clip-path") and (group_attributes[attr] in cur_tag_attributes[attr]): # maybe delete it
                    continue
                cur_tag_attributes[attr] = cur_tag_attributes[attr] + ' ' + group_attributes[attr]
            else:
                cur_tag_attributes[attr] = group_attributes[attr]
        '''
        # Нужно поиследовать, кто там что наследует
        for attr in group_attributes:
            if attr in cur_tag_attributes:
                if attr != "transform":
                    continue
                cur_tag_attributes[attr] = cur_tag_attributes[attr] + ' ' + group_attributes[attr]
            else:
                cur_tag_attributes[attr] = group_attributes[attr]

        tags[i] = add_attributes(cur_tag, cur_tag_attributes)

    return tags


with codecs.open('sample2 (flatten).svg', encoding='utf-8', errors='ignore') as f:
    content = f.read()

tags = []
parsed = re.findall(r"(<.*?/>)|(<.*?>)|(</.*?>)", content)
for tagTuple in parsed:
    tags.append(tagTuple[0] or tagTuple[1] or tagTuple[2])

group_position = find_pair_group(tags)
#counter = 0
while group_position[0] != -1:
    #if counter == 1:
     #   break
    # process one group
    group_attributes = inherit_attributes(tags[group_position[0]])
    tags = extend_attributes(group_attributes, group_position, tags)
    tags.pop(group_position[1])
    tags.pop(group_position[0])
    group_position = find_pair_group(tags)

newContent = '\n'.join(tags)
with open('sample2 (result).svg', 'wb') as f:
    f.write(newContent.encode('utf-8'))





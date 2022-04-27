import PIL.Image
import numpy

def calc_gram(path_to_image):
    pil_image = PIL.Image.open(path_to_image).convert('RGB')
    img_original = numpy.array(pil_image)

    width, height, _ = img_original.shape
    red_flatten = numpy.zeros((width, height), int)
    green_flatten = numpy.zeros((width, height), int)
    blue_flatten = numpy.zeros((width, height), int)
    for i in range(width):
        for j in range(height):
            red_flatten[i][j] = img_original[i][j][0] / 255
            green_flatten[i][j] = img_original[i][j][1] / 255
            blue_flatten[i][j] = img_original[i][j][2] / 255

    return numpy.dot(red_flatten, red_flatten.transpose()), numpy.dot(green_flatten, green_flatten.transpose()), numpy.dot(blue_flatten, blue_flatten.transpose())

def mse(matrix1, matrix2):
    width, height = matrix1.shape
    sum = 0
    for i in range(width):
        for j in range(height):
            sum += ((matrix1[i][j] - matrix2[i][j]) ** 2)
    return sum

def style_loss(result_image, style_image):
    R_red, R_green, R_blue = calc_gram(result_image)
    S_red, S_green, S_blue = calc_gram(style_image)
    channels = 3
    width, height = R_red.shape
    mse_all = (mse(R_red, S_red) + mse(R_green, S_green) + mse(R_blue, S_blue)) / (4.0 * width * height * (channels ** 2))
    
    return mse_all
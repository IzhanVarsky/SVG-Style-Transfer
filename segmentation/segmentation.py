# System libs
import os, csv, torch, numpy, scipy.io, PIL.Image, torchvision.transforms
# Our libs
from mit_semseg.models import ModelBuilder, SegmentationModule
from mit_semseg.utils import colorEncode
import matplotlib.pyplot as plt
import io

class Segmentation:
    NUMBER_OF_CLASSES = 5

    def __init__(self):
        self.colors = scipy.io.loadmat('segmentation/data/color150.mat')['colors']
        self.names = {}
        with open('segmentation/data/object150_info.csv') as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                self.names[int(row[0])] = row[5].split(";")[0]
        # Network Builders
        net_encoder = ModelBuilder.build_encoder(
            arch='resnet50dilated',
            fc_dim=2048,
            weights='segmentation/ckpt/ade20k-resnet50dilated-ppm_deepsup/encoder_epoch_20.pth')
        net_decoder = ModelBuilder.build_decoder(
            arch='ppm_deepsup',
            fc_dim=2048,
            num_class=150,
            weights='segmentation/ckpt/ade20k-resnet50dilated-ppm_deepsup/decoder_epoch_20.pth',
            use_softmax=True)

        crit = torch.nn.NLLLoss(ignore_index=-1)
        self.segmentation_module = SegmentationModule(net_encoder, net_decoder, crit)
        self.segmentation_module.eval()
        self.pil_to_tensor = torchvision.transforms.Compose([
            torchvision.transforms.ToTensor(),
            torchvision.transforms.Normalize(
                mean=[0.485, 0.456, 0.406],  # These are RGB mean+std values
                std=[0.229, 0.224, 0.225])  # across a large photo dataset.
        ])

    '''
    Read the raster image from the path provided via attributes
    from_byte attribute is for reading vector file after we convert it to raster
    (so we can do not save it as file)
    path_to_image = byte array of image if from_byte flag is True
    Return array of masks (simple masks or silhouette if specified) and top-{NUMBER_OF_CLASSES} classes
    '''
    def segment(self, path_to_image, from_byte = False, silhouette = False, predicted_style_obects = None):
        if from_byte:
            pil_image = PIL.Image.open(io.BytesIO(path_to_image)).convert('RGB')
        else:
            pil_image = PIL.Image.open(path_to_image).convert('RGB')
        img_original = numpy.array(pil_image)
        img_data = self.pil_to_tensor(pil_image)
        singleton_batch = {'img_data': img_data[None]}
        output_size = img_data.shape[1:]

        # Run the segmentation at the highest resolution.
        with torch.no_grad():
            scores = self.segmentation_module(singleton_batch, segSize=output_size)

        # Get the predicted scores for each pixel
        _, pred = torch.max(scores, dim=1)
        pred = pred.cpu()[0].numpy()
        predicted_classes = numpy.bincount(pred.flatten()).argsort()[::-1]
        masks = []
        if silhouette:
            # Когда режем маски векторов, у нас уже есть топ-5 классов от стиля (для которых мы маски нарендерели)
            # Нужно посмотреть, нет ли среди 2 * Number_Of_Classes (TODO вот тут)
            # Таких же классов, если что добавляем их, остальное забиваем тем что есть (по приоритету, они уже отсорчены)
            print(predicted_style_obects)
            print(predicted_classes[:self.NUMBER_OF_CLASSES * 2])

            content_classes = []
            cur_free_idx = 0
            for style_class in predicted_style_obects:
                if style_class in predicted_classes[:self.NUMBER_OF_CLASSES * 2]:
                    content_classes.append(style_class)
                else:
                    while predicted_classes[cur_free_idx] in content_classes:
                        cur_free_idx += 1
                    content_classes.append(predicted_classes[cur_free_idx])
            print(content_classes)

            for c in content_classes:
                masks.append(self.__get_silhouette_mask(img_original, pred, c))
        else:
            for c in predicted_classes[:self.NUMBER_OF_CLASSES]:
                masks.append(self.__get_mask(img_original, pred, c))

        return masks, predicted_classes[:self.NUMBER_OF_CLASSES]

    '''
    Return two dimensional array (Row x Column, where each element is array of [R, G, B])
    '''
    def __get_silhouette_mask(self, img, pred, index=None):
        # filter prediction class if requested
        if index is not None:
            pred = pred.copy()
            pred[pred != index] = -1
            #print(f'{self.names[index + 1]}:')

        # colorize prediction
        silhouette_mask = self.__colorize(pred, img).astype(numpy.uint8)

        # aggregate images and save
        compare_images = numpy.concatenate((img, silhouette_mask), axis=1)
        #show image
        plt.imshow(PIL.Image.fromarray(compare_images))
        plt.axis('off')
        plt.show()

        return silhouette_mask

    '''
    Return two dimensional array (Row x Column, where each element is array of [R, G, B])
    '''
    def __get_mask(self, img, pred, index=None):
        # filter prediction class if requested
        if index is not None:
            pred = pred.copy()
            pred[pred != index] = -1
            #print(f'{self.names[index + 1]}:')

        # colorize prediction
        mask = self.__cutMask(pred, img).astype(numpy.uint8)

        # aggregate images and save
        compare_images = numpy.concatenate((img, mask), axis=1)
        #show image
        plt.imshow(PIL.Image.fromarray(compare_images))
        plt.axis('off')
        plt.show()

        return mask

    def __cutMask(self, labelmap, img):
        labelmap = labelmap.astype('int')
        newImage = numpy.zeros((labelmap.shape[0], labelmap.shape[1], 3),
                               dtype=numpy.uint8)

        for i in range(labelmap.shape[0]):
            for j in range(labelmap.shape[1]):
                if labelmap[i][j] < 0:
                    newImage[i][j] = numpy.array([255, 255, 255], int)
                else:
                    newImage[i][j] = img[i][j]

        return newImage

    def __colorize(self, labelmap, img):
        labelmap = labelmap.astype('int')
        newImage = numpy.zeros((labelmap.shape[0], labelmap.shape[1], 3),
                               dtype=numpy.uint8)

        for i in range(labelmap.shape[0]):
            for j in range(labelmap.shape[1]):
                if self.__check_neighbours(i, j, labelmap):
                    newImage[i][j] = numpy.array([255, 255, 255], int)
                else:
                    newImage[i][j] = numpy.array([0, 0, 0], int)

        return newImage

    '''
        Paint border-pixels in black and other pixels in white
        
        Return: true if need to paint it white, false otherwise
    '''
    def __check_neighbours(self, i, j, labelmap):
        ln, lm = labelmap.shape
        return labelmap[i][j] < 0 or \
                (0 < i < ln - 1 and labelmap[i - 1][j] >= 0 and labelmap[i + 1][j] >= 0
                 and 0 < j < lm - 1 and labelmap[i][j - 1] >= 0 and labelmap[i][j + 1] >= 0)
